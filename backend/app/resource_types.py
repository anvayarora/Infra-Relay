from __future__ import annotations

import re

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .audit import audit
from .extensions import db
from .models import Resource, TimestampMixin, uid


resource_types_api = Blueprint(
    "resource_types_api",
    __name__,
    url_prefix="/api/v1",
)


class ResourceType(db.Model, TimestampMixin):
    __tablename__ = "resource_types"

    id = db.Column(
        db.String(40),
        primary_key=True,
        default=lambda: uid("rtype"),
    )
    key = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True,
    )
    name = db.Column(
        db.String(160),
        nullable=False,
    )
    description = db.Column(
        db.Text,
        default="",
        nullable=False,
    )
    fields_json = db.Column(
        db.JSON,
        default=list,
        nullable=False,
    )
    booking_defaults_json = db.Column(
        db.JSON,
        default=dict,
        nullable=False,
    )
    active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
    )


def _slug(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.lower(),
    ).strip("_")


def _normalise_fields(
    raw_fields: list | None,
) -> list[dict]:
    allowed_types = {
        "text",
        "number",
        "boolean",
        "select",
        "textarea",
    }

    fields: list[dict] = []
    seen: set[str] = set()

    for index, raw in enumerate(raw_fields or []):
        if not isinstance(raw, dict):
            continue

        label = str(
            raw.get("label")
            or f"Field {index + 1}"
        ).strip()

        key = _slug(
            str(raw.get("key") or label)
        )

        if not key or key in seen:
            raise ValueError(
                "Every field needs a unique key. "
                f"Duplicate or empty key: {key or 'blank'}"
            )

        field_type = str(
            raw.get("type") or "text"
        )

        if field_type not in allowed_types:
            raise ValueError(
                f"Unsupported field type: {field_type}"
            )

        options = [
            str(option).strip()
            for option in raw.get("options") or []
            if str(option).strip()
        ]

        if field_type == "select" and not options:
            raise ValueError(
                f"Select field '{label}' "
                "needs at least one option"
            )

        fields.append(
            {
                "key": key,
                "label": label,
                "type": field_type,
                "required": bool(
                    raw.get("required")
                ),
                "placeholder": str(
                    raw.get("placeholder") or ""
                ),
                "default": raw.get("default"),
                "options": options,
            }
        )

        seen.add(key)

    return fields


def _booking_defaults(
    raw: dict | None,
) -> dict:
    value = raw or {}

    return {
        "bookable": bool(
            value.get("bookable", True)
        ),
        "approval_required": bool(
            value.get(
                "approval_required",
                False,
            )
        ),
        "maximum_duration_hours": int(
            value.get(
                "maximum_duration_hours",
            )
            or 8
        ),
        "minimum_notice_hours": int(
            value.get(
                "minimum_notice_hours",
            )
            or 0
        ),
        "allow_extensions": bool(
            value.get(
                "allow_extensions",
                True,
            )
        ),
        "cleanup_required": bool(
            value.get(
                "cleanup_required",
                False,
            )
        ),
    }


def resource_type_json(
    item: ResourceType,
) -> dict:
    return {
        "id": item.id,
        "key": item.key,
        "name": item.name,
        "description": item.description,
        "fields": item.fields_json or [],
        "booking_defaults":
            item.booking_defaults_json or {},
        "active": item.active,
        "created_at":
            item.created_at.isoformat(),
        "updated_at":
            item.updated_at.isoformat(),
    }


@resource_types_api.get("/resource-types")
@jwt_required()
def list_resource_types():
    query = ResourceType.query

    if (
        request.args.get("include_inactive")
        != "true"
    ):
        query = query.filter_by(active=True)

    return {
        "items": [
            resource_type_json(item)
            for item in query.order_by(
                ResourceType.name
            ).all()
        ]
    }


@resource_types_api.post("/resource-types")
@jwt_required()
def create_resource_type():
    data = request.get_json(
        silent=True,
    ) or {}

    name = str(
        data.get("name") or ""
    ).strip()

    key = _slug(
        str(data.get("key") or name)
    )

    if not name:
        return {
            "error": "Type name is required"
        }, 422

    if not key:
        return {
            "error": "Type key is required"
        }, 422

    if ResourceType.query.filter_by(
        key=key,
    ).first():
        return {
            "error":
                "A resource type with this "
                "key already exists"
        }, 409

    try:
        fields = _normalise_fields(
            data.get("fields")
        )
        booking_defaults = (
            _booking_defaults(
                data.get(
                    "booking_defaults"
                )
            )
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        return {
            "error": str(exc)
        }, 422

    item = ResourceType(
        key=key,
        name=name,
        description=str(
            data.get("description") or ""
        ).strip(),
        fields_json=fields,
        booking_defaults_json=(
            booking_defaults
        ),
        active=True,
    )

    db.session.add(item)
    db.session.commit()

    audit(
        get_jwt_identity(),
        "resource_type.created",
        "resource_type",
        item.id,
        {"key": item.key},
    )

    return resource_type_json(item), 201


@resource_types_api.put(
    "/resource-types/<resource_type_id>"
)
@jwt_required()
def update_resource_type(
    resource_type_id: str,
):
    item = db.get_or_404(
        ResourceType,
        resource_type_id,
    )

    data = request.get_json(
        silent=True,
    ) or {}

    if "name" in data:
        item.name = (
            str(data["name"] or "").strip()
            or item.name
        )

    if "description" in data:
        item.description = str(
            data["description"] or ""
        ).strip()

    if "active" in data:
        item.active = bool(
            data["active"]
        )

    try:
        if "fields" in data:
            item.fields_json = (
                _normalise_fields(
                    data["fields"]
                )
            )

        if "booking_defaults" in data:
            item.booking_defaults_json = (
                _booking_defaults(
                    data[
                        "booking_defaults"
                    ]
                )
            )
    except (
        TypeError,
        ValueError,
    ) as exc:
        return {
            "error": str(exc)
        }, 422

    db.session.commit()

    audit(
        get_jwt_identity(),
        "resource_type.updated",
        "resource_type",
        item.id,
        {"key": item.key},
    )

    return resource_type_json(item)


@resource_types_api.delete(
    "/resource-types/<resource_type_id>"
)
@jwt_required()
def delete_resource_type(
    resource_type_id: str,
):
    item = db.get_or_404(
        ResourceType,
        resource_type_id,
    )

    if Resource.query.filter_by(
        resource_type=item.key,
    ).first():
        return {
            "error":
                "This type is in use. "
                "Remove or reassign its "
                "resources first."
        }, 409

    type_key = item.key

    db.session.delete(item)
    db.session.commit()

    audit(
        get_jwt_identity(),
        "resource_type.deleted",
        "resource_type",
        resource_type_id,
        {"key": type_key},
    )

    return {"ok": True}
