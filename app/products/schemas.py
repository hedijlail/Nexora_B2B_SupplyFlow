from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    parent_id: str | None = None
    description: str | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None
    is_active: bool


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    category_id: str | None = None
    barcode: str | None = Field(default=None, max_length=100)
    description: str | None = None
    unit: str = Field(default="unit", min_length=1, max_length=30)
    cost_price: float = Field(default=0, ge=0)
    sale_price: float = Field(default=0, ge=0)


class ProductResponse(BaseModel):
    id: str
    sku: str
    name: str
    category_id: str | None
    unit: str
    cost_price: float
    sale_price: float
    is_active: bool
