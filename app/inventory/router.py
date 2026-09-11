import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.inventory.schemas import StockMovementCreate, StockResponse, WarehouseCreate, WarehouseResponse
from app.inventory.service import record_stock_movement

router = APIRouter(prefix="", tags=["inventory"])
INVENTORY_ROLES = ("owner", "admin", "warehouse")
MOVEMENT_TYPES = {"opening", "receipt", "sale", "adjustment", "transfer_in", "transfer_out", "return"}


@router.get("/warehouses", response_model=list[WarehouseResponse])
def list_warehouses(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,code,name,is_active FROM warehouses WHERE company_id=:company_id AND deleted_at IS NULL ORDER BY name
    """), {"company_id": current_user.company_id}).mappings())


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(payload: WarehouseCreate, current_user: CurrentUser = Depends(require_roles(*INVENTORY_ROLES)), db: Session = Depends(get_db)):
    try:
        warehouse = db.execute(text("""
            INSERT INTO warehouses (company_id,code,name,address) VALUES (:company_id,:code,:name,CAST(:address AS jsonb))
            RETURNING id::text,code,name,is_active
        """), {"company_id": current_user.company_id, "code": payload.code, "name": payload.name, "address": json.dumps(payload.address)}).mappings().one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Warehouse code already exists") from exc
    return warehouse


@router.get("/stocks", response_model=list[StockResponse])
def list_stocks(warehouse_id: UUID | None = None, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT s.warehouse_id::text,s.product_id::text,p.sku,p.name AS product_name,s.quantity::float,s.reserved_quantity::float
        FROM stocks s JOIN products p ON p.id=s.product_id AND p.company_id=s.company_id
        WHERE s.company_id=:company_id AND (:warehouse_id IS NULL OR s.warehouse_id=:warehouse_id)
        ORDER BY p.name
    """), {"company_id": current_user.company_id, "warehouse_id": warehouse_id}).mappings())


@router.post("/stock-movements", status_code=status.HTTP_201_CREATED)
def create_stock_movement(payload: StockMovementCreate, current_user: CurrentUser = Depends(require_roles(*INVENTORY_ROLES)), db: Session = Depends(get_db)):
    if payload.movement_type not in MOVEMENT_TYPES:
        raise HTTPException(status_code=422, detail="Invalid movement type")
    try:
        record_stock_movement(db, company_id=current_user.company_id, warehouse_id=UUID(payload.warehouse_id), product_id=UUID(payload.product_id),
                              quantity_delta=payload.quantity_delta, movement_type=payload.movement_type, performed_by=current_user.id,
                              reference_type=payload.reference_type, reference_id=UUID(payload.reference_id) if payload.reference_id else None, notes=payload.notes)
        db.commit()
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Stock movement rejected: check stock, warehouse, and product") from exc
    return {"status": "recorded"}
