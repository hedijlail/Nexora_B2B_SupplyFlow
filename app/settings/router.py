import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_roles
from app.core.audit import write_audit_log
from app.core.database import get_db
from app.settings.schemas import SettingResponse, SettingWrite

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=list[SettingResponse])
def list_settings(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.execute(text("SELECT key,value FROM settings WHERE company_id=:company_id ORDER BY key"), {"company_id": current_user.company_id}).mappings())


@router.put("/{key}", response_model=SettingResponse)
def put_setting(key: str, payload: SettingWrite, current_user: CurrentUser = Depends(require_roles("owner", "admin")), db: Session = Depends(get_db)):
    old_value = db.execute(text("SELECT value FROM settings WHERE company_id=:company_id AND key=:key"), {"company_id": current_user.company_id, "key": key}).scalar_one_or_none()
    setting = db.execute(text("""
        INSERT INTO settings (company_id,key,value) VALUES (:company_id,:key,CAST(:value AS jsonb))
        ON CONFLICT (company_id,key) DO UPDATE SET value=EXCLUDED.value
        RETURNING key,value
    """), {"company_id": current_user.company_id, "key": key, "value": json.dumps(payload.value)}).mappings().one()
    write_audit_log(db, company_id=current_user.company_id, actor_user_id=current_user.id, action="setting.updated", entity_type="setting", old_values={"value": old_value}, new_values={"key": key, "value": payload.value})
    db.commit()
    return setting
