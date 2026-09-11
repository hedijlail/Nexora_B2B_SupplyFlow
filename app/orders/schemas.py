from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    discount_amount: float = Field(default=0, ge=0)
    tax_amount: float = Field(default=0, ge=0)


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItemCreate] = Field(min_length=1)
    notes: str | None = None


class OrderResponse(BaseModel):
    id: str
    order_number: str
    status: str
    subtotal: float
    discount_total: float
    tax_total: float
    grand_total: float


class FulfilOrderRequest(BaseModel):
    warehouse_id: str
