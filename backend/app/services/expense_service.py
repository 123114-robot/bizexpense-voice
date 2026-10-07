from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import ExpenseCategory
from app.models.expense import Expense
from app.models.supplier import Supplier
from app.models.user import User
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseCreate, ExpenseRead


class ExpenseService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.repo = ExpenseRepository(db, user.id)

    def serialize(self, expense: Expense) -> ExpenseRead:
        duplicate = self.repo.find_duplicate(
            expense.supplier_id,
            expense.invoice_number,
            expense.total_amount,
            exclude_id=expense.id,
        )
        return ExpenseRead.model_validate({
            **{field: getattr(expense, field) for field in ExpenseRead.model_fields if hasattr(expense, field)},
            "supplier_name": expense.supplier.name,
            "category_name": expense.category.name,
            "duplicate_warning": duplicate is not None,
            "duplicate_expense_id": duplicate.id if duplicate else None,
        })

    def list(
        self,
        search: str | None = None,
        category_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        ocr_confirmed: bool | None = None,
    ) -> list[ExpenseRead]:
        return [
            self.serialize(item)
            for item in self.repo.list(
                search, category_id, date_from, date_to, ocr_confirmed
            )
        ]

    def get(self, expense_id: int) -> ExpenseRead:
        expense = self.repo.get(expense_id)
        if not expense:
            raise HTTPException(404, "Expense not found")
        return self.serialize(expense)

    def _references(self, payload: ExpenseCreate):
        category = self.db.get(ExpenseCategory, payload.category_id)
        if not category:
            raise HTTPException(422, "Invalid category")
        supplier = self.db.scalar(select(Supplier).where(Supplier.user_id == self.user.id, Supplier.name == payload.supplier_name))
        if supplier is None:
            supplier = Supplier(user_id=self.user.id, name=payload.supplier_name, abn=payload.supplier_abn)
            self.db.add(supplier)
            self.db.flush()
        return supplier, category

    def create(self, payload: ExpenseCreate) -> ExpenseRead:
        supplier, category = self._references(payload)
        data = payload.model_dump(exclude={"supplier_name", "supplier_abn", "category_id"})
        expense = Expense(**data, user_id=self.user.id, supplier_id=supplier.id, category_id=category.id)
        return self.serialize(self.repo.save(expense))

    def update(self, expense_id: int, payload: ExpenseCreate) -> ExpenseRead:
        expense = self.repo.get(expense_id)
        if not expense:
            raise HTTPException(404, "Expense not found")
        supplier, category = self._references(payload)
        for key, value in payload.model_dump(exclude={"supplier_name", "supplier_abn", "category_id"}).items():
            setattr(expense, key, value)
        expense.supplier_id = supplier.id
        expense.category_id = category.id
        return self.serialize(self.repo.save(expense))

    def delete(self, expense_id: int) -> None:
        expense = self.repo.get(expense_id)
        if not expense:
            raise HTTPException(404, "Expense not found")
        self.repo.delete(expense)
