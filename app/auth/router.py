from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.auth.schemas import BootstrapRequest, LoginRequest, TokenResponse
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/bootstrap", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def bootstrap(payload: BootstrapRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Create the first tenant and its owner. Available only on an empty database."""
    if db.execute(text("SELECT EXISTS (SELECT 1 FROM companies)")).scalar():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform has already been initialized")
    try:
        company = db.execute(text("""
            INSERT INTO companies (name, slug) VALUES (:name, :slug) RETURNING id
        """), {"name": payload.company_name, "slug": payload.company_slug}).mappings().one()
        user = db.execute(text("""
            INSERT INTO users (company_id, email, password_hash, full_name, role)
            VALUES (:company_id, :email, :password_hash, :full_name, 'owner') RETURNING id, role
        """), {"company_id": company["id"], "email": str(payload.email).lower(), "password_hash": hash_password(payload.password), "full_name": payload.full_name}).mappings().one()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company or email already exists") from exc
    return TokenResponse(access_token=create_access_token(user_id=user["id"], company_id=company["id"], role=user["role"]))


@router.post("/token", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(text("""
        SELECT u.id, u.company_id, u.role, u.password_hash
        FROM users u JOIN companies c ON c.id = u.company_id
        WHERE c.slug = :slug AND c.is_active = true AND u.email = :email AND u.is_active = true
    """), {"slug": payload.company_slug, "email": str(payload.email).lower()}).mappings().one_or_none()
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect company, email, or password")
    db.execute(text("UPDATE users SET last_login_at = now() WHERE id = :id"), {"id": user["id"]})
    db.commit()
    return TokenResponse(access_token=create_access_token(user_id=user["id"], company_id=user["company_id"], role=user["role"]))


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"id": current_user.id, "company_id": current_user.company_id, "role": current_user.role}
