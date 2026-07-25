from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from .extensions import db

def uid(prefix: str) -> str: return f"{prefix}_{uuid4().hex[:16]}"
def utcnow() -> datetime: return datetime.now(timezone.utc)
class TimestampMixin:
    created_at=db.Column(db.DateTime(timezone=True),default=utcnow,nullable=False)
    updated_at=db.Column(db.DateTime(timezone=True),default=utcnow,onupdate=utcnow,nullable=False)
class User(db.Model,TimestampMixin):
    __tablename__="users";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("usr"));email=db.Column(db.String(255),unique=True,nullable=False);name=db.Column(db.String(160),nullable=False);role=db.Column(db.String(40),default="admin",nullable=False)
class CredentialReference(db.Model,TimestampMixin):
    __tablename__="credential_references";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("cred"));name=db.Column(db.String(160),nullable=False);kind=db.Column(db.String(80),nullable=False);metadata_json=db.Column(db.JSON,default=dict,nullable=False);encrypted_payload=db.Column(db.Text);active=db.Column(db.Boolean,default=True,nullable=False)
class Resource(db.Model,TimestampMixin):
    __tablename__="resources";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("res"));name=db.Column(db.String(180),nullable=False);resource_type=db.Column(db.String(80),nullable=False);status=db.Column(db.String(40),default="available",nullable=False);location=db.Column(db.String(180),default="",nullable=False);connection_ref=db.Column(db.String(40));capabilities_json=db.Column(db.JSON,default=dict,nullable=False);booking_policy_json=db.Column(db.JSON,default=dict,nullable=False);maintenance_json=db.Column(db.JSON,default=dict,nullable=False);tags_json=db.Column(db.JSON,default=list,nullable=False)
class Booking(db.Model,TimestampMixin):
    __tablename__="bookings";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("book"));resource_id=db.Column(db.String(40),db.ForeignKey("resources.id"),nullable=False);requested_by=db.Column(db.String(255),nullable=False);purpose=db.Column(db.String(500),default="",nullable=False);starts_at=db.Column(db.DateTime(timezone=True),nullable=False);ends_at=db.Column(db.DateTime(timezone=True),nullable=False);status=db.Column(db.String(40),default="confirmed",nullable=False);metadata_json=db.Column(db.JSON,default=dict,nullable=False);resource=db.relationship("Resource")
class Workflow(db.Model,TimestampMixin):
    __tablename__="workflows";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("wf"));name=db.Column(db.String(180),nullable=False);description=db.Column(db.Text,default="",nullable=False);status=db.Column(db.String(40),default="draft",nullable=False);current_version=db.Column(db.Integer,default=1,nullable=False);graph_json=db.Column(db.JSON,default=dict,nullable=False);settings_json=db.Column(db.JSON,default=dict,nullable=False);created_by=db.Column(db.String(255),nullable=False)
class Sandbox(db.Model,TimestampMixin):
    __tablename__="sandboxes";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("sbx"));name=db.Column(db.String(180),nullable=False);slug=db.Column(db.String(180),unique=True,nullable=False);description=db.Column(db.Text,default="",nullable=False);status=db.Column(db.String(40),default="active",nullable=False);environment=db.Column(db.String(40),default="development",nullable=False);workflow_ids_json=db.Column(db.JSON,default=list,nullable=False);settings_json=db.Column(db.JSON,default=dict,nullable=False);interface_manifest_json=db.Column(db.JSON,default=dict,nullable=False)
class SandboxAttachment(db.Model,TimestampMixin):
    __tablename__="sandbox_attachments"
    id=db.Column(db.String(40),primary_key=True,default=lambda:uid("att"))
    sandbox_id=db.Column(db.String(40),db.ForeignKey("sandboxes.id"),nullable=False,index=True)
    name=db.Column(db.String(180),nullable=False)
    attachment_type=db.Column(db.String(60),nullable=False)
    provider=db.Column(db.String(80),default="custom",nullable=False)
    status=db.Column(db.String(40),default="active",nullable=False)
    credential_ref=db.Column(db.String(40),nullable=True)
    config_json=db.Column(db.JSON,default=dict,nullable=False)
    scopes_json=db.Column(db.JSON,default=list,nullable=False)
    sandbox=db.relationship("Sandbox")
class Execution(db.Model,TimestampMixin):
    __tablename__="executions";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("exec"));workflow_id=db.Column(db.String(40),db.ForeignKey("workflows.id"),nullable=False);sandbox_id=db.Column(db.String(40),db.ForeignKey("sandboxes.id"));status=db.Column(db.String(40),default="queued",nullable=False);trigger_type=db.Column(db.String(60),default="manual",nullable=False);input_json=db.Column(db.JSON,default=dict,nullable=False);context_json=db.Column(db.JSON,default=dict,nullable=False);output_json=db.Column(db.JSON,default=dict,nullable=False);error=db.Column(db.Text);started_at=db.Column(db.DateTime(timezone=True));completed_at=db.Column(db.DateTime(timezone=True));workflow=db.relationship("Workflow");sandbox=db.relationship("Sandbox")
class BlockExecution(db.Model,TimestampMixin):
    __tablename__="block_executions";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("bex"));execution_id=db.Column(db.String(40),db.ForeignKey("executions.id"),nullable=False);block_id=db.Column(db.String(120),nullable=False);block_type=db.Column(db.String(120),nullable=False);status=db.Column(db.String(40),default="queued",nullable=False);input_json=db.Column(db.JSON,default=dict,nullable=False);output_json=db.Column(db.JSON,default=dict,nullable=False);error=db.Column(db.Text);started_at=db.Column(db.DateTime(timezone=True));completed_at=db.Column(db.DateTime(timezone=True))
class UITransaction(db.Model,TimestampMixin):
    __tablename__="ui_transactions";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("uitx"));execution_id=db.Column(db.String(40),db.ForeignKey("executions.id"),nullable=False);sandbox_id=db.Column(db.String(40),db.ForeignKey("sandboxes.id"));workflow_id=db.Column(db.String(40),nullable=False);block_id=db.Column(db.String(120),nullable=False);direction=db.Column(db.String(30),nullable=False);status=db.Column(db.String(40),default="open",nullable=False);intent=db.Column(db.String(160),default="interaction",nullable=False);schema_json=db.Column(db.JSON,default=dict,nullable=False);payload_json=db.Column(db.JSON,default=dict,nullable=False);response_json=db.Column(db.JSON,default=dict,nullable=False);allowed_actions_json=db.Column(db.JSON,default=list,nullable=False);token=db.Column(db.String(160),unique=True,nullable=False);expires_at=db.Column(db.DateTime(timezone=True));responded_at=db.Column(db.DateTime(timezone=True));responded_by=db.Column(db.String(255))
class ExecutionEvent(db.Model):
    __tablename__="execution_events";id=db.Column(db.Integer,primary_key=True,autoincrement=True);execution_id=db.Column(db.String(40),nullable=False,index=True);sandbox_id=db.Column(db.String(40),index=True);event_type=db.Column(db.String(120),nullable=False);payload_json=db.Column(db.JSON,default=dict,nullable=False);created_at=db.Column(db.DateTime(timezone=True),default=utcnow,nullable=False)
class AuditEvent(db.Model):
    __tablename__="audit_events";id=db.Column(db.String(40),primary_key=True,default=lambda:uid("audit"));actor=db.Column(db.String(255),nullable=False);action=db.Column(db.String(160),nullable=False);target_type=db.Column(db.String(100),nullable=False);target_id=db.Column(db.String(100),nullable=False);payload_json=db.Column(db.JSON,default=dict,nullable=False);created_at=db.Column(db.DateTime(timezone=True),default=utcnow,nullable=False)
