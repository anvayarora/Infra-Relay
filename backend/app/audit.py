from .extensions import db
from .models import AuditEvent

def audit(actor: str, action: str, target_type: str, target_id: str, payload: dict | None = None):
    db.session.add(AuditEvent(actor=actor, action=action, target_type=target_type, target_id=target_id, payload_json=payload or {}))
    db.session.commit()
