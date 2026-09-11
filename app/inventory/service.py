"""Inventory writes are ledgered and atomic."""
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class InsufficientStockError(ValueError):
    pass


def record_stock_movement(
    session: Session, *, company_id: UUID, warehouse_id: UUID, product_id: UUID,
    quantity_delta: float, movement_type: str, performed_by: UUID | None = None,
    reference_type: str | None = None, reference_id: UUID | None = None, notes: str | None = None,
) -> None:
    """Change stock and append its immutable ledger entry in the same transaction.

    The UPDATE locks the stock row. The database CHECK constraint remains the
    final guard against negative stock, including concurrent requests.
    """
    if quantity_delta == 0:
        raise ValueError("quantity_delta cannot be zero")

    session.execute(text("""
        INSERT INTO stocks (company_id, warehouse_id, product_id, quantity)
        VALUES (:company_id, :warehouse_id, :product_id, 0)
        ON CONFLICT (company_id, warehouse_id, product_id) DO NOTHING
    """), {"company_id": company_id, "warehouse_id": warehouse_id, "product_id": product_id})
    result = session.execute(text("""
        UPDATE stocks SET quantity = quantity + :delta
        WHERE company_id = :company_id AND warehouse_id = :warehouse_id AND product_id = :product_id
        RETURNING quantity
    """), {"company_id": company_id, "warehouse_id": warehouse_id, "product_id": product_id, "delta": quantity_delta})
    if result.scalar_one() < 0:
        # Defensive only; the database CHECK should reject the update first.
        raise InsufficientStockError("insufficient stock")
    session.execute(text("""
        INSERT INTO stock_movements (company_id, warehouse_id, product_id, movement_type, quantity_delta, performed_by, reference_type, reference_id, notes)
        VALUES (:company_id, :warehouse_id, :product_id, CAST(:movement_type AS stock_movement_type), :delta, :performed_by, :reference_type, :reference_id, :notes)
    """), {"company_id": company_id, "warehouse_id": warehouse_id, "product_id": product_id, "movement_type": movement_type,
           "delta": quantity_delta, "performed_by": performed_by, "reference_type": reference_type, "reference_id": reference_id, "notes": notes})
