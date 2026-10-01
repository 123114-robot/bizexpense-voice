from decimal import Decimal

from pydantic import BaseModel, Field


class PrepareExpenseRequest(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=180)
    amount: Decimal = Field(gt=0, decimal_places=2)
    invoice_date: str = Field(min_length=5, max_length=20)
    category_name: str | None = Field(default=None, max_length=120)


class PrepareExpenseUpdateRequest(BaseModel):
    category_name: str = Field(min_length=1, max_length=120)
