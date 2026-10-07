from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.category import ExpenseCategory
from app.models.expense import Expense
from app.models.supplier import Supplier


class DashboardService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def summary(self) -> dict:
        total, gst, count = self.db.execute(
            select(func.coalesce(func.sum(Expense.total_amount), 0), func.coalesce(func.sum(Expense.gst_amount), 0), func.count(Expense.id))
            .where(Expense.ocr_confirmed.is_(True), Expense.user_id == self.user_id)
        ).one()
        today = date.today()
        month_total = self.db.scalar(
            select(func.coalesce(func.sum(Expense.total_amount), 0)).where(
                Expense.ocr_confirmed.is_(True),
                Expense.user_id == self.user_id,
                extract("year", Expense.invoice_date) == today.year,
                extract("month", Expense.invoice_date) == today.month,
            )
        )
        category_rows = self.db.execute(
            select(
                ExpenseCategory.name,
                func.sum(Expense.total_amount).label("total"),
                func.count(Expense.id).label("expense_count"),
            )
            .join(Expense, Expense.category_id == ExpenseCategory.id)
            .where(Expense.ocr_confirmed.is_(True), Expense.user_id == self.user_id)
            .group_by(ExpenseCategory.id, ExpenseCategory.name)
            .order_by(func.sum(Expense.total_amount).desc())
        ).all()
        supplier_rows = self.db.execute(
            select(
                Supplier.name,
                func.sum(Expense.total_amount).label("total"),
                func.count(Expense.id).label("expense_count"),
            )
            .join(Expense, Expense.supplier_id == Supplier.id)
            .where(
                Expense.ocr_confirmed.is_(True),
                Expense.user_id == self.user_id,
                Supplier.user_id == self.user_id,
            )
            .group_by(Supplier.id, Supplier.name)
            .order_by(func.sum(Expense.total_amount).desc())
            .limit(5)
        ).all()

        first_month_index = today.year * 12 + today.month - 1 - 5
        first_month = date(first_month_index // 12, first_month_index % 12 + 1, 1)
        year_expression = extract("year", Expense.invoice_date)
        month_expression = extract("month", Expense.invoice_date)
        monthly_rows = self.db.execute(
            select(
                year_expression.label("year"),
                month_expression.label("month"),
                func.sum(Expense.total_amount).label("total"),
            )
            .where(
                Expense.ocr_confirmed.is_(True),
                Expense.user_id == self.user_id,
                Expense.invoice_date >= first_month,
            )
            .group_by(year_expression, month_expression)
            .order_by(year_expression, month_expression)
        ).all()
        totals_by_month = {
            f"{int(row.year):04d}-{int(row.month):02d}": Decimal(row.total)
            for row in monthly_rows
        }
        monthly_trend = []
        for offset in range(6):
            month_index = first_month_index + offset
            month_key = f"{month_index // 12:04d}-{month_index % 12 + 1:02d}"
            monthly_trend.append(
                {"month": month_key, "total": f"{totals_by_month.get(month_key, Decimal(0)):.2f}"}
            )
        return {
            "total_expenses": f"{Decimal(total):.2f}",
            "expenses_this_month": f"{Decimal(month_total or 0):.2f}",
            "gst_paid": f"{Decimal(gst):.2f}",
            "expense_count": count,
            "average_expense": (
                f"{Decimal(total) / count:.2f}" if count else "0.00"
            ),
            "top_suppliers": [
                {
                    "supplier": row.name,
                    "total": f"{Decimal(row.total):.2f}",
                    "expense_count": row.expense_count,
                }
                for row in supplier_rows
            ],
            "category_breakdown": [
                {
                    "category": row.name,
                    "total": f"{Decimal(row.total):.2f}",
                    "expense_count": row.expense_count,
                }
                for row in category_rows
            ],
            "monthly_trend": monthly_trend,
        }
