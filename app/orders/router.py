from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.inventory.service import record_stock_movement
from app.orders.schemas import FulfilOrderRequest, OrderCreate, OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])
SALES_ROLES = ("owner", "admin", "sales")
FULFIL_ROLES = ("owner", "admin", "warehouse")


def next_order_number() -> str:
    return f"ORD-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"


@router.get("", response_model=list[OrderResponse])
def list_orders(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,order_number,status::text,subtotal::float,discount_total::float,tax_total::float,grand_total::float
        FROM orders WHERE company_id=:company_id ORDER BY order_date DESC
    """), {"company_id": current_user.company_id}).mappings())


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, current_user: CurrentUser = Depends(require_roles(*SALES_ROLES)), db: Session = Depends(get_db)):
    company_id = current_user.company_id
    try:
        customer_id = UUID(payload.customer_id)
        customer_exists = db.execute(text("SELECT 1 FROM customers WHERE id=:id AND company_id=:company_id AND is_active=true AND deleted_at IS NULL"), {"id": customer_id, "company_id": company_id}).scalar()
        if not customer_exists:
            raise HTTPException(status_code=404, detail="Active customer not found")
        order = db.execute(text("""
            INSERT INTO orders (company_id,customer_id,order_number,notes,created_by)
            VALUES (:company_id,:customer_id,:order_number,:notes,:created_by) RETURNING id
        """), {"company_id": company_id, "customer_id": customer_id, "order_number": next_order_number(), "notes": payload.notes, "created_by": current_user.id}).mappings().one()
        subtotal = discount_total = tax_total = 0.0
        for item in payload.items:
            product_id = UUID(item.product_id)
            product = db.execute(text("""
                SELECT COALESCE((SELECT cp.unit_price FROM customer_pricing cp
                    WHERE cp.company_id=:company_id AND cp.customer_id=:customer_id AND cp.product_id=p.id AND cp.is_active=true
                      AND (cp.valid_from IS NULL OR cp.valid_from <= CURRENT_DATE) AND (cp.valid_to IS NULL OR cp.valid_to >= CURRENT_DATE)
                      AND cp.min_quantity <= :quantity ORDER BY cp.min_quantity DESC LIMIT 1), p.sale_price) AS unit_price
                FROM products p WHERE p.id=:product_id AND p.company_id=:company_id AND p.is_active=true AND p.deleted_at IS NULL
            """), {"company_id": company_id, "customer_id": customer_id, "product_id": product_id, "quantity": item.quantity}).mappings().one_or_none()
            if product is None:
                raise HTTPException(status_code=404, detail="Active product not found")
            unit_price = float(product["unit_price"])
            line_total = (item.quantity * unit_price) - item.discount_amount + item.tax_amount
            if line_total < 0:
                raise HTTPException(status_code=422, detail="Item discount cannot exceed its value plus tax")
            db.execute(text("""
                INSERT INTO order_items (company_id,order_id,product_id,quantity,unit_price,discount_amount,tax_amount,line_total)
                VALUES (:company_id,:order_id,:product_id,:quantity,:unit_price,:discount_amount,:tax_amount,:line_total)
            """), {"company_id": company_id, "order_id": order["id"], "product_id": product_id, "quantity": item.quantity, "unit_price": unit_price,
                   "discount_amount": item.discount_amount, "tax_amount": item.tax_amount, "line_total": line_total})
            subtotal += item.quantity * unit_price
            discount_total += item.discount_amount
            tax_total += item.tax_amount
        order = db.execute(text("""
            UPDATE orders SET subtotal=:subtotal,discount_total=:discount_total,tax_total=:tax_total,grand_total=:grand_total WHERE id=:id
            RETURNING id::text,order_number,status::text,subtotal::float,discount_total::float,tax_total::float,grand_total::float
        """), {"id": order["id"], "subtotal": subtotal, "discount_total": discount_total, "tax_total": tax_total, "grand_total": subtotal-discount_total+tax_total}).mappings().one()
        db.commit()
        return order
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Invalid order data") from exc
    except HTTPException:
        db.rollback()
        raise


@router.post("/{order_id}/confirm", response_model=OrderResponse)
def confirm_order(order_id: UUID, current_user: CurrentUser = Depends(require_roles(*SALES_ROLES)), db: Session = Depends(get_db)):
    order = db.execute(text("""
        UPDATE orders SET status='confirmed' WHERE id=:id AND company_id=:company_id AND status='draft'
        RETURNING id::text,order_number,status::text,subtotal::float,discount_total::float,tax_total::float,grand_total::float
    """), {"id": order_id, "company_id": current_user.company_id}).mappings().one_or_none()
    if order is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="Only draft orders can be confirmed")
    db.commit()
    return order


@router.post("/{order_id}/fulfil", response_model=OrderResponse)
def fulfil_order(order_id: UUID, payload: FulfilOrderRequest, current_user: CurrentUser = Depends(require_roles(*FULFIL_ROLES)), db: Session = Depends(get_db)):
    """Fulfil the whole confirmed order atomically from one warehouse."""
    try:
        warehouse_id = UUID(payload.warehouse_id)
        order = db.execute(text("""
            SELECT id,status::text FROM orders WHERE id=:id AND company_id=:company_id FOR UPDATE
        """), {"id": order_id, "company_id": current_user.company_id}).mappings().one_or_none()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        if order["status"] not in {"confirmed", "processing"}:
            raise HTTPException(status_code=409, detail="Only confirmed orders can be fulfilled")
        items = db.execute(text("""
            SELECT product_id,quantity FROM order_items WHERE order_id=:order_id AND company_id=:company_id
        """), {"order_id": order_id, "company_id": current_user.company_id}).mappings()
        for item in items:
            record_stock_movement(db, company_id=current_user.company_id, warehouse_id=warehouse_id, product_id=item["product_id"],
                                  quantity_delta=-float(item["quantity"]), movement_type="sale", performed_by=current_user.id,
                                  reference_type="order", reference_id=order_id)
        fulfilled = db.execute(text("""
            UPDATE orders SET status='fulfilled' WHERE id=:id AND company_id=:company_id
            RETURNING id::text,order_number,status::text,subtotal::float,discount_total::float,tax_total::float,grand_total::float
        """), {"id": order_id, "company_id": current_user.company_id}).mappings().one()
        db.commit()
        return fulfilled
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Fulfilment failed: check warehouse and available stock") from exc
    except HTTPException:
        db.rollback()
        raise
