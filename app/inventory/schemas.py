from pydantic import BaseModel, Field


class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    address: dict = Field(default_factory=dict)


class WarehouseResponse(BaseModel):
    id: str
    code: str
    name: str
    is_active: bool


class StockResponse(BaseModel):
    warehouse_id: str
    product_id: str
    sku: str
    product_name: str
    quantity: float
    reserved_quantity: float


class StockMovementCreate(BaseModel):
    warehouse_id: str
    product_id: str
    movement_type: str
    quantity_delta: float
    reference_type: str | None = Field(default=None, max_length=50)
    reference_id: str | None = None
    notes: str | None = None
