from datetime import datetime
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    action: str
    entity_type: str
    entity_id: str | None
    actor_user_id: str | None
    created_at: datetime
