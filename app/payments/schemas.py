from datetime import date
from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float = Field(gt=0)
    payment_date: date | None = None
    method: str | None = Field(default=None, max_length=50)
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class PaymentResponse(BaseModel):
    id: str
    payment_number: str
    invoice_id: str
    status: str
    amount: float
