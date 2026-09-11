from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.schemas import AuditLogResponse
from app.auth.dependencies import CurrentUser, require_roles
from app.core.database import get_db

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(limit: int = 100, current_user: CurrentUser = Depends(require_roles("owner", "admin")), db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 500)
    return list(db.execute(text("""
        SELECT id::text,action,entity_type,entity_id::text,actor_user_id::text,created_at
        FROM audit_logs WHERE company_id=:company_id ORDER BY created_at DESC LIMIT :limit
    """), {"company_id": current_user.company_id, "limit": limit}).mappings())
