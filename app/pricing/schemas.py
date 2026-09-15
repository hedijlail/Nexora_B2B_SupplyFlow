from datetime import date

from pydantic import BaseModel, Field, model_validator


class CustomerPriceCreate(BaseModel):
    customer_id: str
    product_id: str
    unit_price: float = Field(ge=0)
    min_quantity: float = Field(default=1, gt=0)
    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        return self


class CustomerPriceUpdate(BaseModel):
    unit_price: float | None = Field(default=None, ge=0)
    min_quantity: float | None = Field(default=None, gt=0)
    valid_from: date | None = None
    valid_to: date | None = None
    is_active: bool | None = None


class CustomerPriceResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    product_id: str
    product_sku: str
    product_name: str
    unit_price: float
    min_quantity: float
    valid_from: date | None
    valid_to: date | None
    is_active: bool
