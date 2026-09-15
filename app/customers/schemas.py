from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    tax_id: str | None = Field(default=None, max_length=100)
    address: dict = Field(default_factory=dict)
    credit_limit: float = Field(default=0, ge=0)
    payment_terms_days: int = Field(default=0, ge=0)

class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    tax_id: str | None = Field(default=None, max_length=100)
    address: dict | None = None
    credit_limit: float | None = Field(default=None, ge=0)
    payment_terms_days: int | None = Field(default=None, ge=0)



class CustomerResponse(BaseModel):
    id: str
    code: str
    name: str
    email: EmailStr | None
    phone: str | None
    credit_limit: float
    payment_terms_days: int
    is_active: bool

class CustomerDetailResponse(BaseModel):
    id: str
    code: str
    name: str
    email: EmailStr | None
    phone: str | None
    tax_id: str | None
    address: dict
    credit_limit: float
    payment_terms_days: int
    is_active: bool
    created_at: object
    updated_at: object