from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.expense import Expense
from app.models.supplier import Supplier


class ExpenseRepository:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def list(
        self,
        search: str | None = None,
        category_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ocr_confirmed: bool | None = None,
    ) -> list[Expense]:
        statement = select(Expense).options(joinedload(Expense.supplier), joinedload(Expense.category)).where(Expense.user_id == self.user_id).order_by(Expense.invoice_date.desc())
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.join(Supplier).where(
                or_(Expense.description.ilike(pattern), Supplier.name.ilike(pattern))
            )
        if category_id is not None:
            statement = statement.where(Expense.category_id == category_id)
        if date_from is not None:
            statement = statement.where(Expense.invoice_date >= date_from)
        if date_to is not None:
            statement = statement.where(Expense.invoice_date <= date_to)
        if ocr_confirmed is not None:
            statement = statement.where(Expense.ocr_confirmed.is_(ocr_confirmed))
        return list(self.db.scalars(statement).all())

    def get(self, expense_id: int) -> Expense | None:
        return self.db.scalar(select(Expense).options(joinedload(Expense.supplier), joinedload(Expense.category)).where(Expense.id == expense_id, Expense.user_id == self.user_id))

    def find_duplicate(
        self,
        supplier_id: int,
        invoice_number: str | None,
        total_amount: Decimal,
        exclude_id: int | None = None,
    ) -> Expense | None:
        if not invoice_number or not invoice_number.strip():
            return None
        statement = select(Expense).where(
            Expense.user_id == self.user_id,
            Expense.supplier_id == supplier_id,
            Expense.invoice_number == invoice_number,
            Expense.total_amount == total_amount,
        )
        if exclude_id is not None:
            statement = statement.where(Expense.id != exclude_id)
        return self.db.scalar(statement.order_by(Expense.id).limit(1))

    def save(self, expense: Expense) -> Expense:
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return self.get(expense.id)  # type: ignore[return-value]

    def delete(self, expense: Expense) -> None:
        self.db.delete(expense)
        self.db.commit()
