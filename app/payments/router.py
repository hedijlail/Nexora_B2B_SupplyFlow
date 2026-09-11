from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.payments.schemas import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments", tags=["payments"])
PAYMENT_ROLES = ("owner", "admin", "accountant")


def next_payment_number() -> str:
    return f"PAY-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"


@router.get("", response_model=list[PaymentResponse])
def list_payments(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,payment_number,invoice_id::text,status::text,amount::float
        FROM payments WHERE company_id=:company_id ORDER BY created_at DESC
    """), {"company_id": current_user.company_id}).mappings())


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(payload: PaymentCreate, current_user: CurrentUser = Depends(require_roles(*PAYMENT_ROLES)), db: Session = Depends(get_db)):
    try:
        invoice_id = UUID(payload.invoice_id)
        invoice = db.execute(text("""
            SELECT id,grand_total,status::text FROM invoices
            WHERE id=:id AND company_id=:company_id FOR UPDATE
        """), {"id": invoice_id, "company_id": current_user.company_id}).mappings().one_or_none()
        if invoice is None or invoice["status"] not in {"issued", "partially_paid"}:
            raise HTTPException(status_code=409, detail="Invoice is not payable")
        paid = db.execute(text("""
            SELECT COALESCE(SUM(amount),0) FROM payments WHERE invoice_id=:invoice_id AND company_id=:company_id AND status='completed'
        """), {"invoice_id": invoice_id, "company_id": current_user.company_id}).scalar_one()
        if float(paid) + payload.amount > float(invoice["grand_total"]) + 0.00001:
            raise HTTPException(status_code=422, detail="Payment exceeds outstanding balance")
        payment = db.execute(text("""
            INSERT INTO payments (company_id,invoice_id,payment_number,status,amount,payment_date,method,reference,notes)
            VALUES (:company_id,:invoice_id,:payment_number,'completed',:amount,COALESCE(:payment_date,CURRENT_DATE),:method,:reference,:notes)
            RETURNING id::text,payment_number,invoice_id::text,status::text,amount::float
        """), {"company_id": current_user.company_id, "invoice_id": invoice_id, "payment_number": next_payment_number(), **payload.model_dump(exclude={"invoice_id"})}).mappings().one()
        new_paid = float(paid) + payload.amount
        new_status = "paid" if abs(new_paid - float(invoice["grand_total"])) < 0.00001 else "partially_paid"
        db.execute(text("UPDATE invoices SET status=CAST(:status AS invoice_status) WHERE id=:id AND company_id=:company_id"), {"status": new_status, "id": invoice_id, "company_id": current_user.company_id})
        db.commit()
        return payment
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail="Invalid payment") from exc
    except HTTPException:
        db.rollback()
        raise
