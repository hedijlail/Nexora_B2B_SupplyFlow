from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.users.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
VALID_ROLES = {"admin", "sales", "warehouse", "accountant", "viewer"}


@router.get("", response_model=list[UserResponse])
def list_users(current_user: CurrentUser = Depends(require_roles("owner", "admin")), db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT id::text, email, full_name, role::text, is_active FROM users WHERE company_id=:company_id ORDER BY created_at"), {"company_id": current_user.company_id}).mappings()
    return list(rows)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, current_user: CurrentUser = Depends(require_roles("owner", "admin")), db: Session = Depends(get_db)):
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail="Invalid assignable role")
    try:
        user = db.execute(text("""
            INSERT INTO users (company_id,email,password_hash,full_name,role)
            VALUES (:company_id,:email,:password_hash,:full_name,CAST(:role AS user_role))
            RETURNING id::text,email,full_name,role::text,is_active
        """), {"company_id": current_user.company_id, "email": str(payload.email).lower(), "password_hash": hash_password(payload.password), "full_name": payload.full_name, "role": payload.role}).mappings().one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists for this company") from exc
    return user
