import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_roles,
)
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.customers.schemas import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerResponse,
    CustomerUpdate,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    search: str | None = Query(default=None, max_length=100),
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conditions = """
        company_id = :company_id
        AND deleted_at IS NULL
    """

    params = {
        "company_id": current_user.company_id,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }

    if search:
        conditions += """
            AND (
                code ILIKE :search
                OR name ILIKE :search
                OR email ILIKE :search
                OR phone ILIKE :search
                OR tax_id ILIKE :search
            )
        """
        params["search"] = f"%{search}%"

    if is_active is not None:
        conditions += " AND is_active = :is_active"
        params["is_active"] = is_active

    result = db.execute(
        text(f"""
            SELECT
                id::text,
                code,
                name,
                email,
                phone,
                credit_limit::float,
                payment_terms_days,
                is_active
            FROM customers
            WHERE {conditions}
            ORDER BY name
            LIMIT :limit OFFSET :offset
        """),
        params,
    )

    return list(result.mappings())


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(
    customer_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = db.execute(
        text("""
            SELECT
                id::text,
                code,
                name,
                email,
                phone,
                tax_id,
                address,
                credit_limit::float,
                payment_terms_days,
                is_active,
                created_at,
                updated_at
            FROM customers
            WHERE id = :id
                AND company_id = :company_id
                AND deleted_at IS NULL
        """),
        {
            "id": customer_id,
            "company_id": current_user.company_id,
        },
    ).mappings().one_or_none()

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return customer


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    payload: CustomerCreate,
    current_user: CurrentUser = Depends(
        require_roles("owner", "admin", "sales")
    ),
    db: Session = Depends(get_db),
):
    try:
        customer = db.execute(
            text("""
                INSERT INTO customers (
                    company_id,
                    code,
                    name,
                    email,
                    phone,
                    tax_id,
                    address,
                    credit_limit,
                    payment_terms_days
                )
                VALUES (
                    :company_id,
                    :code,
                    :name,
                    :email,
                    :phone,
                    :tax_id,
                    CAST(:address AS jsonb),
                    :credit_limit,
                    :payment_terms_days
                )
                RETURNING
                    id::text,
                    code,
                    name,
                    email,
                    phone,
                    credit_limit::float,
                    payment_terms_days,
                    is_active
            """),
            {
                "company_id": current_user.company_id,
                "code": payload.code,
                "name": payload.name,
                "email": payload.email,
                "phone": payload.phone,
                "tax_id": payload.tax_id,
                "address": json.dumps(payload.address),
                "credit_limit": payload.credit_limit,
                "payment_terms_days": payload.payment_terms_days,
            },
        ).mappings().one()

        write_audit_log(
            db,
            company_id=current_user.company_id,
            actor_user_id=current_user.id,
            action="CUSTOMER_CREATED",
            entity_type="customer",
            entity_id=UUID(customer["id"]),
            new_values=dict(customer),
        )

        db.commit()

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer code already exists",
        ) from exc

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    current_user: CurrentUser = Depends(
        require_roles("owner", "admin", "sales")
    ),
    db: Session = Depends(get_db),
):
    old_customer = db.execute(
        text("""
            SELECT
                id::text,
                code,
                name,
                email,
                phone,
                tax_id,
                address,
                credit_limit::float,
                payment_terms_days,
                is_active
            FROM customers
            WHERE id = :id
                AND company_id = :company_id
                AND deleted_at IS NULL
        """),
        {
            "id": customer_id,
            "company_id": current_user.company_id,
        },
    ).mappings().one_or_none()

    if old_customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    set_clauses = []
    params = {
        "id": customer_id,
        "company_id": current_user.company_id,
    }

    for field, value in updates.items():
        if field == "address":
            set_clauses.append("address = CAST(:address AS jsonb)")
            params["address"] = json.dumps(value)
        else:
            set_clauses.append(f"{field} = :{field}")
            params[field] = value

    set_clauses.append("updated_at = now()")

    result = db.execute(
        text(f"""
            UPDATE customers
            SET {", ".join(set_clauses)}
            WHERE id = :id
                AND company_id = :company_id
                AND deleted_at IS NULL
            RETURNING
                id::text,
                code,
                name,
                email,
                phone,
                credit_limit::float,
                payment_terms_days,
                is_active
        """),
        params,
    ).mappings().one()

    write_audit_log(
        db,
        company_id=current_user.company_id,
        actor_user_id=current_user.id,
        action="CUSTOMER_UPDATED",
        entity_type="customer",
        entity_id=customer_id,
        old_values=dict(old_customer),
        new_values=dict(result),
    )

    db.commit()

    return result


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_customer(
    customer_id: UUID,
    current_user: CurrentUser = Depends(
        require_roles("owner", "admin")
    ),
    db: Session = Depends(get_db),
):
    old_customer = db.execute(
        text("""
            SELECT
                id::text,
                code,
                name,
                is_active
            FROM customers
            WHERE id = :id
                AND company_id = :company_id
                AND deleted_at IS NULL
        """),
        {
            "id": customer_id,
            "company_id": current_user.company_id,
        },
    ).mappings().one_or_none()

    if old_customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    db.execute(
        text("""
            UPDATE customers
            SET
                is_active = false,
                deleted_at = now(),
                updated_at = now()
            WHERE id = :id
                AND company_id = :company_id
                AND deleted_at IS NULL
        """),
        {
            "id": customer_id,
            "company_id": current_user.company_id,
        },
    )

    write_audit_log(
        db,
        company_id=current_user.company_id,
        actor_user_id=current_user.id,
        action="CUSTOMER_DEACTIVATED",
        entity_type="customer",
        entity_id=customer_id,
        old_values=dict(old_customer),
        new_values={
            "is_active": False,
            "deleted_at": "now",
        },
    )

    db.commit()
