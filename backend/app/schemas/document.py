from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    mime_type: str
    uploaded_at: datetime


class OCRResult(BaseModel):
    supplier_name: str
    abn: str | None = None
    invoice_number: str | None = None
    invoice_date: date
    due_date: date | None = None
    subtotal: Decimal
    gst: Decimal
    total: Decimal
    currency: str = "AUD"
    confidence: float = Field(ge=0, le=1)
    confirmed: bool = False

    @field_validator("subtotal", "gst", "total")
    @classmethod
    def amounts_must_be_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Amounts cannot be negative")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO code")
        return normalized

    @model_validator(mode="after")
    def validate_accounting_totals(self):
        if self.gst > self.total:
            raise ValueError("GST cannot exceed total")
        return self
