from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from threading import Lock
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import ExpenseCategory
from app.models.user import User
from app.schemas.expense import ExpenseCreate
from app.schemas.voice import PrepareExpenseRequest, PrepareExpenseUpdateRequest
from app.services.dashboard_service import DashboardService
from app.services.expense_service import ExpenseService


@dataclass
class PendingAction:
    user_id: int
    action: str
    payload: ExpenseCreate
    expense_id: int | None
    expires_at: datetime
    executing: bool = False
    executed: bool = False


class PendingActionStore:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._actions: dict[str, PendingAction] = {}
        self._lock = Lock()

    def create(
        self,
        action: str,
        payload: ExpenseCreate,
        user_id: int,
        expense_id: int | None = None,
    ) -> str:
        action_id = str(uuid4())
        with self._lock:
            self._actions[action_id] = PendingAction(
                user_id=user_id,
                action=action,
                payload=payload,
                expense_id=expense_id,
                expires_at=datetime.now(UTC) + timedelta(seconds=self.ttl_seconds),
            )
        return action_id

    def claim(self, action_id: str, user_id: int) -> PendingAction:
        with self._lock:
            pending = self._actions.get(action_id)
            if pending is None:
                raise HTTPException(404, "Pending action not found")
            if pending.user_id != user_id:
                raise HTTPException(404, "Pending action not found")
            if pending.expires_at <= datetime.now(UTC):
                del self._actions[action_id]
                raise HTTPException(410, "Pending action expired")
            if pending.executed:
                raise HTTPException(409, "Pending action already executed")
            if pending.executing:
                raise HTTPException(409, "Pending action is already executing")
            pending.executing = True
            return pending

    def finish(self, action_id: str) -> None:
        with self._lock:
            pending = self._actions[action_id]
            pending.executing = False
            pending.executed = True

    def release(self, action_id: str) -> None:
        with self._lock:
            pending = self._actions.get(action_id)
            if pending is not None and not pending.executed:
                pending.executing = False

    def cancel(self, action_id: str, user_id: int) -> None:
        with self._lock:
            pending = self._actions.get(action_id)
            if pending is None or pending.user_id != user_id:
                raise HTTPException(404, "Pending action not found")
            del self._actions[action_id]

    def clear(self) -> None:
        with self._lock:
            self._actions.clear()


class VoiceService:
    def __init__(
        self, db: Session, pending_actions: PendingActionStore, user: User
    ):
        self.db = db
        self.pending_actions = pending_actions
        self.user = user

    def _category(self, name: str | None) -> ExpenseCategory:
        category_name = (name or "Other").strip()
        category = self.db.scalar(
            select(ExpenseCategory).where(
                func.lower(ExpenseCategory.name) == category_name.lower()
            )
        )
        if category is None:
            raise HTTPException(422, f"Unknown category: {category_name}")
        return category

    @staticmethod
    def _invoice_date(value: str) -> date:
        normalized = value.strip().lower()
        if normalized == "today":
            return date.today()
        if normalized == "yesterday":
            return date.today() - timedelta(days=1)
        try:
            return date.fromisoformat(normalized)
        except ValueError as exc:
            raise HTTPException(
                422, "invoice_date must be today, yesterday, or YYYY-MM-DD"
            ) from exc

    def summary(self) -> dict:
        return DashboardService(self.db, self.user.id).summary()

    def prepare_expense(self, request: PrepareExpenseRequest) -> dict:
        category = self._category(request.category_name)
        amount = request.amount.quantize(Decimal("0.01"))
        payload = ExpenseCreate(
            supplier_name=request.supplier_name.strip(),
            category_id=category.id,
            invoice_date=self._invoice_date(request.invoice_date),
            subtotal=amount,
            gst_amount=Decimal("0.00"),
            total_amount=amount,
            currency="AUD",
            description="Voice-created expense",
            ocr_confirmed=True,
        )
        action_id = self.pending_actions.create(
            "create_expense", payload, self.user.id
        )
        return {
            "status": "confirmation_required",
            "pending_action_id": action_id,
            "action": "create_expense",
            "preview": {
                "supplier_name": payload.supplier_name,
                "amount": f"{payload.total_amount:.2f}",
                "invoice_date": payload.invoice_date.isoformat(),
                "category_name": category.name,
                "currency": payload.currency,
            },
        }

    def prepare_update(self, request: PrepareExpenseUpdateRequest) -> dict:
        category = self._category(request.category_name)
        expenses = ExpenseService(self.db, self.user).list(ocr_confirmed=True)
        if not expenses:
            raise HTTPException(404, "No confirmed expense is available to update")
        latest = expenses[0]
        payload = ExpenseCreate(
            supplier_name=latest.supplier_name,
            category_id=category.id,
            document_id=latest.document_id,
            invoice_number=latest.invoice_number,
            invoice_date=latest.invoice_date,
            due_date=latest.due_date,
            subtotal=latest.subtotal,
            gst_amount=latest.gst_amount,
            total_amount=latest.total_amount,
            currency=latest.currency,
            description=latest.description,
            ocr_confidence=latest.ocr_confidence,
            ocr_confirmed=latest.ocr_confirmed,
        )
        action_id = self.pending_actions.create(
            "update_expense", payload, self.user.id, expense_id=latest.id
        )
        return {
            "status": "confirmation_required",
            "pending_action_id": action_id,
            "action": "update_expense",
            "preview": {
                "expense_id": latest.id,
                "supplier_name": latest.supplier_name,
                "amount": f"{latest.total_amount:.2f}",
                "current_category": latest.category_name,
                "proposed_category": category.name,
            },
        }

    def confirm(self, action_id: str) -> dict:
        pending = self.pending_actions.claim(action_id, self.user.id)
        service = ExpenseService(self.db, self.user)
        try:
            if pending.action == "create_expense":
                expense = service.create(pending.payload)
            elif pending.action == "update_expense" and pending.expense_id is not None:
                expense = service.update(pending.expense_id, pending.payload)
            else:
                raise HTTPException(422, "Unsupported pending action")
        except Exception:
            self.pending_actions.release(action_id)
            raise
        self.pending_actions.finish(action_id)
        return {
            "status": "executed",
            "action": pending.action,
            "expense": expense.model_dump(mode="json"),
        }
