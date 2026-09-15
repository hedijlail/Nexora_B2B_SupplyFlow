"""Small, explicit audit writer for state-changing application services."""
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def write_audit_log(session: Session, *, company_id: UUID, action: str, entity_type: str, actor_user_id: UUID | None = None,
                    entity_id: UUID | None = None, old_values: dict | None = None, new_values: dict | None = None) -> None:
    session.execute(text("""
        INSERT INTO audit_logs (company_id,actor_user_id,action,entity_type,entity_id,old_values,new_values)
        VALUES (:company_id,:actor_user_id,:action,:entity_type,:entity_id,CAST(:old_values AS jsonb),CAST(:new_values AS jsonb))
    """), {"company_id": company_id, "actor_user_id": actor_user_id, "action": action, "entity_type": entity_type,
           "entity_id": entity_id, "old_values": json.dumps(old_values, default=str) if old_values is not None else None,
           "new_values": json.dumps(new_values, default=str) if new_values is not None else None})
