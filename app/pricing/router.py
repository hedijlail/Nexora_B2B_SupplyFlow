from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.pricing.schemas import CustomerPriceCreate, CustomerPriceResponse, CustomerPriceUpdate

router = APIRouter(prefix="/customer-pricing", tags=["pricing"])
WRITE_ROLES = ("owner", "admin", "sales")

_RETURNING = """
    cp.id::text, cp.customer_id::text, c.name AS customer_name,
    cp.product_id::text, p.sku AS product_sku, p.name AS product_name,
    cp.unit_price::float, cp.min_quantity::float, cp.valid_from, cp.valid_to, cp.is_active
"""


@router.get("", response_model=list[CustomerPriceResponse])
def list_customer_prices(
    customer_id: UUID | None = None,
    product_id: UUID | None = None,
    active_only: bool = True,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list(db.execute(text(f"""
        SELECT {_RETURNING}
        FROM customer_pricing cp
        JOIN customers c ON c.id=cp.customer_id AND c.company_id=cp.company_id
        JOIN products p ON p.id=cp.product_id AND p.company_id=cp.company_id
        WHERE cp.company_id=:company_id
          AND (:customer_id IS NULL OR cp.customer_id=:customer_id)
          AND (:product_id IS NULL OR cp.product_id=:product_id)
          AND (:active_only=false OR cp.is_active=true)
        ORDER BY c.name,p.name,cp.min_quantity DESC
    """), {"company_id": current_user.company_id, "customer_id": customer_id, "product_id": product_id, "active_only": active_only}).mappings())


@router.post("", response_model=CustomerPriceResponse, status_code=status.HTTP_201_CREATED)
def create_customer_price(
    payload: CustomerPriceCreate,
    current_user: CurrentUser = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    try:
        customer_id, product_id = UUID(payload.customer_id), UUID(payload.product_id)
        price = db.execute(text(f"""
            WITH created AS (
                INSERT INTO customer_pricing (company_id,customer_id,product_id,unit_price,min_quantity,valid_from,valid_to)
                VALUES (:company_id,:customer_id,:product_id,:unit_price,:min_quantity,:valid_from,:valid_to)
                RETURNING *
            )
            SELECT {_RETURNING.replace('cp.', 'created.')}
            FROM created
            JOIN customers c ON c.id=created.customer_id AND c.company_id=created.company_id
            JOIN products p ON p.id=created.product_id AND p.company_id=created.company_id
        """), {"company_id": current_user.company_id, "customer_id": customer_id, "product_id": product_id,
               "unit_price": payload.unit_price, "min_quantity": payload.min_quantity,
               "valid_from": payload.valid_from, "valid_to": payload.valid_to}).mappings().one()
        write_audit_log(db, company_id=current_user.company_id, actor_user_id=current_user.id, action="customer_price.created", entity_type="customer_pricing", entity_id=UUID(price["id"]), new_values=dict(price))
        db.commit()
        return price
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Invalid customer, product, or price") from exc


@router.patch("/{price_id}", response_model=CustomerPriceResponse)
def update_customer_price(
    price_id: UUID,
    payload: CustomerPriceUpdate,
    current_user: CurrentUser = Depends(require_roles(*WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    old = db.execute(text("SELECT id::text,unit_price::float,min_quantity::float,valid_from,valid_to,is_active FROM customer_pricing WHERE id=:id AND company_id=:company_id"), {"id": price_id, "company_id": current_user.company_id}).mappings().one_or_none()
    if old is None:
        raise HTTPException(status_code=404, detail="Customer price not found")
    merged_from = updates.get("valid_from", old["valid_from"])
    merged_to = updates.get("valid_to", old["valid_to"])
    if merged_from and merged_to and merged_to < merged_from:
        raise HTTPException(status_code=422, detail="valid_to must be on or after valid_from")
    clauses = ", ".join(f"{field}=:{field}" for field in updates)
    params = {"id": price_id, "company_id": current_user.company_id, **updates}
    db.execute(text(f"UPDATE customer_pricing SET {clauses} WHERE id=:id AND company_id=:company_id"), params)
    price = db.execute(text(f"""
        SELECT {_RETURNING} FROM customer_pricing cp
        JOIN customers c ON c.id=cp.customer_id AND c.company_id=cp.company_id
        JOIN products p ON p.id=cp.product_id AND p.company_id=cp.company_id
        WHERE cp.id=:id AND cp.company_id=:company_id
    """), {"id": price_id, "company_id": current_user.company_id}).mappings().one()
    write_audit_log(db, company_id=current_user.company_id, actor_user_id=current_user.id, action="customer_price.updated", entity_type="customer_pricing", entity_id=price_id, old_values=dict(old), new_values=dict(price))
    db.commit()
    return price
