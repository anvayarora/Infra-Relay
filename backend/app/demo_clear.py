from __future__ import annotations

from app import create_app
from app.extensions import db
from app.models import (
    AuditEvent,
    BlockExecution,
    Booking,
    CredentialReference,
    Execution,
    ExecutionEvent,
    Resource,
    Sandbox,
    SandboxAttachment,
    UITransaction,
    User,
    Workflow,
)

try:
    from app.resource_types import ResourceType
except Exception:
    ResourceType = None


PREFIX = "demo_"


def main() -> None:
    app = create_app({"SEED_DATA": False, "REQUEUE_EXECUTIONS": False})

    with app.app_context():
        UITransaction.query.filter(UITransaction.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        BlockExecution.query.filter(BlockExecution.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        ExecutionEvent.query.filter(ExecutionEvent.execution_id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        Execution.query.filter(Execution.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        Booking.query.filter(Booking.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        SandboxAttachment.query.filter(SandboxAttachment.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        Sandbox.query.filter(Sandbox.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        Workflow.query.filter(Workflow.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        Resource.query.filter(Resource.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        CredentialReference.query.filter(CredentialReference.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        AuditEvent.query.filter(AuditEvent.id.like(f"{PREFIX}%")).delete(synchronize_session=False)
        User.query.filter(User.id.like(f"{PREFIX}%")).delete(synchronize_session=False)

        if ResourceType is not None:
            ResourceType.query.filter(ResourceType.id.like(f"{PREFIX}%")).delete(synchronize_session=False)

        db.session.commit()
        print("InfraRelay demo data removed. Non-demo records were not changed.")


if __name__ == "__main__":
    main()
