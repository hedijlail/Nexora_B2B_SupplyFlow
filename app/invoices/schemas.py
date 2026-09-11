from datetime import date
from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    due_date: date | None = None
    notes: str | None = None


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    order_id: str | None
    status: str
    issue_date: date
    due_date: date | None
    grand_total: float
