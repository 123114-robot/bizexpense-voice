from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExpenseCreate(BaseModel):
    supplier_name: str = Field(min_length=1, max_length=180)
    supplier_abn: str | None = Field(default=None, max_length=20)
    category_id: int
    document_id: int | None = None
    invoice_number: str | None = Field(default=None, max_length=100)
    invoice_date: date
    due_date: date | None = None
    subtotal: Decimal = Field(ge=0, decimal_places=2)
    gst_amount: Decimal = Field(ge=0, decimal_places=2)
    total_amount: Decimal = Field(ge=0, decimal_places=2)
    currency: str = Field(default="AUD", min_length=3, max_length=3)
    description: str = Field(min_length=1)
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    ocr_confirmed: bool = False

    @model_validator(mode="after")
    def validate_amounts(self):
        if self.gst_amount > self.total_amount:
            raise ValueError("GST cannot exceed total amount")
        return self


class ExpenseUpdate(ExpenseCreate):
    pass


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    supplier_id: int
    supplier_name: str
    category_id: int
    category_name: str
    document_id: int | None
    invoice_number: str | None
    invoice_date: date
    due_date: date | None
    subtotal: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    currency: str
    description: str
    ocr_confidence: float | None
    ocr_confirmed: bool
    created_at: datetime
    updated_at: datetime
    duplicate_warning: bool = False
    duplicate_expense_id: int | None = None
