from __future__ import annotations
from datetime import datetime

def iso(value: datetime | None):
    return value.isoformat() if value else None

def model_dict(obj, fields):
    return {field: iso(getattr(obj, field)) if isinstance(getattr(obj, field), datetime) else getattr(obj, field) for field in fields}
