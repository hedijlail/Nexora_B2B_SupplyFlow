import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.customers.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerResponse])
def list_customers(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,code,name,email,phone,credit_limit::float,payment_terms_days,is_active
        FROM customers WHERE company_id=:company_id AND deleted_at IS NULL ORDER BY name
    """), {"company_id": current_user.company_id}).mappings())


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, current_user: CurrentUser = Depends(require_roles("owner", "admin", "sales")), db: Session = Depends(get_db)):
    try:
        customer = db.execute(text("""
            INSERT INTO customers (company_id,code,name,email,phone,tax_id,address,credit_limit,payment_terms_days)
            VALUES (:company_id,:code,:name,:email,:phone,:tax_id,CAST(:address AS jsonb),:credit_limit,:payment_terms_days)
            RETURNING id::text,code,name,email,phone,credit_limit::float,payment_terms_days,is_active
        """), {"company_id": current_user.company_id, **payload.model_dump(mode="json", exclude={"address"}), "address": json.dumps(payload.address)}).mappings().one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Customer code already exists") from exc
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_customer(customer_id: UUID, current_user: CurrentUser = Depends(require_roles("owner", "admin")), db: Session = Depends(get_db)):
    result = db.execute(text("""
        UPDATE customers SET is_active=false,deleted_at=now() WHERE id=:id AND company_id=:company_id AND deleted_at IS NULL
    """), {"id": customer_id, "company_id": current_user.company_id})
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=404, detail="Customer not found")
    db.commit()
