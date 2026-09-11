from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.database import get_db
from app.products.schemas import CategoryCreate, CategoryResponse, ProductCreate, ProductResponse

router = APIRouter(prefix="", tags=["catalogue"])
WRITE_ROLES = ("owner", "admin", "sales")


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,name,parent_id::text,is_active FROM categories
        WHERE company_id=:company_id AND deleted_at IS NULL ORDER BY name
    """), {"company_id": current_user.company_id}).mappings())


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, current_user: CurrentUser = Depends(require_roles(*WRITE_ROLES)), db: Session = Depends(get_db)):
    try:
        category = db.execute(text("""
            INSERT INTO categories (company_id,name,parent_id,description)
            VALUES (:company_id,:name,:parent_id,:description)
            RETURNING id::text,name,parent_id::text,is_active
        """), {"company_id": current_user.company_id, **payload.model_dump()}).mappings().one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name or parent is invalid") from exc
    return category


@router.get("/products", response_model=list[ProductResponse])
def list_products(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("""
        SELECT id::text,sku,name,category_id::text,unit,cost_price::float,sale_price::float,is_active
        FROM products WHERE company_id=:company_id AND deleted_at IS NULL ORDER BY name
    """), {"company_id": current_user.company_id}).mappings())


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, current_user: CurrentUser = Depends(require_roles(*WRITE_ROLES)), db: Session = Depends(get_db)):
    try:
        product = db.execute(text("""
            INSERT INTO products (company_id,sku,name,category_id,barcode,description,unit,cost_price,sale_price)
            VALUES (:company_id,:sku,:name,:category_id,:barcode,:description,:unit,:cost_price,:sale_price)
            RETURNING id::text,sku,name,category_id::text,unit,cost_price::float,sale_price::float,is_active
        """), {"company_id": current_user.company_id, **payload.model_dump()}).mappings().one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product SKU, barcode, or category is invalid") from exc
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_product(product_id: UUID, current_user: CurrentUser = Depends(require_roles("owner", "admin")), db: Session = Depends(get_db)):
    result = db.execute(text("""
        UPDATE products SET is_active=false,deleted_at=now() WHERE id=:id AND company_id=:company_id AND deleted_at IS NULL
    """), {"id": product_id, "company_id": current_user.company_id})
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=404, detail="Product not found")
    db.commit()
