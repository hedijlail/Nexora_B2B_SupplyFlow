from datetime import date, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.invoices.schemas import InvoiceCreate, InvoiceResponse

router = APIRouter(prefix="/invoices", tags=["invoices"])
INVOICE_ROLES = ("owner", "admin", "accountant", "sales")


def next_invoice_number() -> str:
    return f"INV-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,invoice_number,order_id::text,status::text,issue_date,due_date,grand_total::float
        FROM invoices WHERE company_id=:company_id ORDER BY issue_date DESC,created_at DESC
    """), {"company_id": current_user.company_id}).mappings())


@router.post("/from-order/{order_id}", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice_from_order(order_id: UUID, payload: InvoiceCreate, current_user: CurrentUser = Depends(require_roles(*INVOICE_ROLES)), db: Session = Depends(get_db)):
    try:
        order = db.execute(text("""
            SELECT o.customer_id,o.subtotal,o.tax_total,o.grand_total,c.payment_terms_days
            FROM orders o JOIN customers c ON c.id=o.customer_id AND c.company_id=o.company_id
            WHERE o.id=:order_id AND o.company_id=:company_id AND o.status='fulfilled' FOR UPDATE
        """), {"order_id": order_id, "company_id": current_user.company_id}).mappings().one_or_none()
        if order is None:
            raise HTTPException(status_code=409, detail="Only fulfilled orders can be invoiced")
        if db.execute(text("SELECT 1 FROM invoices WHERE company_id=:company_id AND order_id=:order_id AND status <> 'void'"), {"company_id": current_user.company_id, "order_id": order_id}).scalar():
            raise HTTPException(status_code=409, detail="Order already has an active invoice")
        due_date = payload.due_date or date.today() + timedelta(days=order["payment_terms_days"])
        invoice = db.execute(text("""
            INSERT INTO invoices (company_id,customer_id,order_id,invoice_number,status,issue_date,due_date,subtotal,tax_total,grand_total,notes)
            VALUES (:company_id,:customer_id,:order_id,:invoice_number,'issued',CURRENT_DATE,:due_date,:subtotal,:tax_total,:grand_total,:notes)
            RETURNING id::text,invoice_number,order_id::text,status::text,issue_date,due_date,grand_total::float
        """), {"company_id": current_user.company_id, "customer_id": order["customer_id"], "order_id": order_id,
               "invoice_number": next_invoice_number(), "due_date": due_date, "subtotal": order["subtotal"], "tax_total": order["tax_total"], "grand_total": order["grand_total"], "notes": payload.notes}).mappings().one()
        db.commit()
        return invoice
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invoice could not be created") from exc
    except HTTPException:
        db.rollback()
        raise
