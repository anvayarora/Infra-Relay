from __future__ import annotations

from datetime import timedelta

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
    utcnow,
)

try:
    from app.resource_types import ResourceType
except Exception:
    ResourceType = None


DEMO_PREFIX = "demo_"
ADMIN_EMAIL = "demo.admin@infrarelay.local"


def graph(nodes: list[dict], edges: list[dict]) -> dict:
    return {"nodes": nodes, "edges": edges}


def node(node_id: str, block_type: str, label: str, x: int, y: int, settings: dict) -> dict:
    return {
        "id": node_id,
        "type": block_type,
        "position": {"x": x, "y": y},
        "data": {
            "label": label,
            "blockType": block_type,
            "settings": settings,
        },
    }


def edge(edge_id: str, source: str, target: str, source_handle: str | None = None) -> dict:
    value = {"id": edge_id, "source": source, "target": target}
    if source_handle:
        value["sourceHandle"] = source_handle
    return value


def clear_demo() -> None:
    UITransaction.query.filter(UITransaction.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    BlockExecution.query.filter(BlockExecution.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    ExecutionEvent.query.filter(ExecutionEvent.execution_id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    Execution.query.filter(Execution.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    Booking.query.filter(Booking.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    SandboxAttachment.query.filter(SandboxAttachment.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    Sandbox.query.filter(Sandbox.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    Workflow.query.filter(Workflow.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    Resource.query.filter(Resource.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    CredentialReference.query.filter(CredentialReference.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    AuditEvent.query.filter(AuditEvent.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    User.query.filter(User.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    if ResourceType is not None:
        ResourceType.query.filter(ResourceType.id.like(f"{DEMO_PREFIX}%")).delete(synchronize_session=False)
    db.session.commit()


def seed_resource_types(now):
    if ResourceType is None:
        return

    types = [
        ResourceType(
            id="demo_rtype_gpu_server",
            key="gpu_server",
            name="GPU Server",
            description="Physical or virtual compute equipped with NVIDIA GPUs.",
            fields_json=[
                {"key": "hostname", "label": "Hostname", "type": "text", "required": True, "placeholder": "gpu-node-01", "options": []},
                {"key": "ip_address", "label": "IP address", "type": "text", "required": True, "placeholder": "10.25.60.41", "options": []},
                {"key": "gpu_model", "label": "GPU model", "type": "select", "required": True, "options": ["NVIDIA H100", "NVIDIA H200", "NVIDIA A100", "NVIDIA L40S"]},
                {"key": "gpu_count", "label": "GPU count", "type": "number", "required": True, "options": []},
                {"key": "operating_system", "label": "Operating system", "type": "select", "required": True, "options": ["Ubuntu 22.04", "Ubuntu 24.04", "RHEL 9", "Rocky Linux 9"]},
            ],
            booking_defaults_json={
                "bookable": True,
                "approval_required": True,
                "maximum_duration_hours": 24,
                "minimum_notice_hours": 2,
                "allow_extensions": True,
                "cleanup_required": True,
            },
            active=True,
            created_at=now - timedelta(days=30),
            updated_at=now - timedelta(hours=2),
        ),
        ResourceType(
            id="demo_rtype_virtual_machine",
            key="virtual_machine",
            name="Virtual Machine",
            description="Managed virtual compute instance.",
            fields_json=[
                {"key": "hostname", "label": "Hostname", "type": "text", "required": True, "options": []},
                {"key": "cpu_cores", "label": "CPU cores", "type": "number", "required": True, "options": []},
                {"key": "memory_gb", "label": "Memory (GB)", "type": "number", "required": True, "options": []},
                {"key": "operating_system", "label": "Operating system", "type": "select", "required": True, "options": ["Ubuntu 24.04", "RHEL 9", "Windows Server 2025"]},
            ],
            booking_defaults_json={
                "bookable": True,
                "approval_required": False,
                "maximum_duration_hours": 72,
                "minimum_notice_hours": 0,
                "allow_extensions": True,
                "cleanup_required": True,
            },
            active=True,
            created_at=now - timedelta(days=28),
            updated_at=now - timedelta(days=1),
        ),
        ResourceType(
            id="demo_rtype_cluster_namespace",
            key="cluster_namespace",
            name="Cluster Namespace",
            description="Bookable Kubernetes namespace with quota controls.",
            fields_json=[
                {"key": "cluster", "label": "Cluster", "type": "text", "required": True, "options": []},
                {"key": "namespace", "label": "Namespace", "type": "text", "required": True, "options": []},
                {"key": "gpu_quota", "label": "GPU quota", "type": "number", "required": False, "options": []},
            ],
            booking_defaults_json={
                "bookable": True,
                "approval_required": False,
                "maximum_duration_hours": 12,
                "minimum_notice_hours": 0,
                "allow_extensions": True,
                "cleanup_required": True,
            },
            active=True,
            created_at=now - timedelta(days=24),
            updated_at=now - timedelta(days=2),
        ),
    ]
    db.session.add_all(types)


def main() -> None:
    app = create_app({"SEED_DATA": False, "REQUEUE_EXECUTIONS": False})

    with app.app_context():
        clear_demo()
        now = utcnow()

        db.session.add(
            User(
                id="demo_usr_admin",
                email=ADMIN_EMAIL,
                name="Platform Administrator",
                role="admin",
                created_at=now - timedelta(days=45),
                updated_at=now - timedelta(minutes=5),
            )
        )

        seed_resource_types(now)

        credentials = [
            CredentialReference(
                id="demo_cred_ad",
                name="Corporate Active Directory",
                kind="active_directory",
                metadata_json={"host": "dc01.corp.example", "domain": "CORP", "mode": "winrm", "demo": True},
                encrypted_payload=None,
                active=True,
                created_at=now - timedelta(days=21),
                updated_at=now - timedelta(days=1),
            ),
            CredentialReference(
                id="demo_cred_gpu",
                name="GPU Fleet SSH",
                kind="ssh",
                metadata_json={"username": "svc-gpu-ops", "port": 22, "demo": True},
                encrypted_payload=None,
                active=True,
                created_at=now - timedelta(days=20),
                updated_at=now - timedelta(hours=8),
            ),
            CredentialReference(
                id="demo_cred_smtp",
                name="Infrastructure SMTP Relay",
                kind="smtp",
                metadata_json={"host": "smtp.corp.example", "port": 25, "tls": False, "demo": True},
                encrypted_payload=None,
                active=True,
                created_at=now - timedelta(days=19),
                updated_at=now - timedelta(days=2),
            ),
        ]
        db.session.add_all(credentials)

        resources = [
            Resource(
                id="demo_res_gpu_01",
                name="GPU Cluster H200-01",
                resource_type="gpu_server",
                status="available",
                location="Bengaluru GPU Lab",
                connection_ref="demo_cred_gpu",
                capabilities_json={"hostname": "gpu-h200-01", "ip_address": "10.25.60.41", "gpu_model": "NVIDIA H200", "gpu_count": 8, "cpu_cores": 192, "memory_gb": 2048, "operating_system": "Ubuntu 24.04"},
                booking_policy_json={"bookable": True, "approval_required": True, "maximum_duration_hours": 24, "minimum_notice_hours": 2, "allow_extensions": True, "cleanup_required": True},
                maintenance_json={"driver_version": "570.172.08", "cuda_version": "12.8", "container_toolkit_version": "1.19.1", "health": "healthy", "last_checked": (now - timedelta(minutes=18)).isoformat()},
                tags_json=["gpu", "h200", "production", "training"],
                created_at=now - timedelta(days=30),
                updated_at=now - timedelta(minutes=18),
            ),
            Resource(
                id="demo_res_gpu_02",
                name="GPU Cluster H100-02",
                resource_type="gpu_server",
                status="maintenance",
                location="Bengaluru GPU Lab",
                connection_ref="demo_cred_gpu",
                capabilities_json={"hostname": "gpu-h100-02", "ip_address": "10.25.60.42", "gpu_model": "NVIDIA H100", "gpu_count": 8, "cpu_cores": 160, "memory_gb": 1536, "operating_system": "RHEL 9"},
                booking_policy_json={"bookable": True, "approval_required": True, "maximum_duration_hours": 24, "minimum_notice_hours": 4, "allow_extensions": False, "cleanup_required": True},
                maintenance_json={"driver_version": "550.90.07", "cuda_version": "12.4", "container_toolkit_version": "1.17.8", "health": "maintenance", "reboot_required": True},
                tags_json=["gpu", "h100", "maintenance"],
                created_at=now - timedelta(days=27),
                updated_at=now - timedelta(minutes=42),
            ),
            Resource(
                id="demo_res_esxi_01",
                name="Virtualisation Host 03",
                resource_type="physical_server",
                status="reserved",
                location="Primary Datacentre",
                connection_ref=None,
                capabilities_json={"hostname": "esxi-03", "ip_address": "10.25.60.53", "vendor": "HPE", "cpu_cores": 96, "memory_gb": 1024, "hypervisor": "VMware ESXi 8"},
                booking_policy_json={"bookable": True, "approval_required": True, "maximum_duration_hours": 48, "minimum_notice_hours": 1, "allow_extensions": True, "cleanup_required": False},
                maintenance_json={"health": "healthy"},
                tags_json=["vmware", "compute", "shared"],
                created_at=now - timedelta(days=26),
                updated_at=now - timedelta(hours=1),
            ),
            Resource(
                id="demo_res_vm_01",
                name="Application Validation VM",
                resource_type="virtual_machine",
                status="available",
                location="Engineering Cluster",
                connection_ref="demo_cred_gpu",
                capabilities_json={"hostname": "app-validation-01", "cpu_cores": 16, "memory_gb": 64, "operating_system": "Ubuntu 24.04"},
                booking_policy_json={"bookable": True, "approval_required": False, "maximum_duration_hours": 72, "minimum_notice_hours": 0, "allow_extensions": True, "cleanup_required": True},
                maintenance_json={"health": "healthy"},
                tags_json=["vm", "engineering", "validation"],
                created_at=now - timedelta(days=18),
                updated_at=now - timedelta(hours=3),
            ),
            Resource(
                id="demo_res_namespace_01",
                name="GPU Training Namespace",
                resource_type="cluster_namespace",
                status="available",
                location="Training Kubernetes Cluster",
                connection_ref=None,
                capabilities_json={"cluster": "training-cluster-01", "namespace": "gpu-lab", "gpu_quota": 2, "memory_gb": 128},
                booking_policy_json={"bookable": True, "approval_required": False, "maximum_duration_hours": 12, "minimum_notice_hours": 0, "allow_extensions": True, "cleanup_required": True},
                maintenance_json={"health": "healthy"},
                tags_json=["kubernetes", "gpu", "training"],
                created_at=now - timedelta(days=16),
                updated_at=now - timedelta(hours=6),
            ),
            Resource(
                id="demo_res_storage_01",
                name="AI Dataset Storage Pool",
                resource_type="storage_pool",
                status="available",
                location="Primary Datacentre",
                connection_ref=None,
                capabilities_json={"capacity_tb": 120, "available_tb": 47, "protocol": "NFS", "performance_tier": "high"},
                booking_policy_json={"bookable": True, "approval_required": True, "maximum_duration_hours": 720, "minimum_notice_hours": 12, "allow_extensions": True, "cleanup_required": False},
                maintenance_json={"health": "healthy"},
                tags_json=["storage", "ai", "shared"],
                created_at=now - timedelta(days=15),
                updated_at=now - timedelta(days=1),
            ),
        ]
        db.session.add_all(resources)

        resource_graph = graph(
            [
                node("start", "trigger.manual", "Start request", 60, 180, {}),
                node("collect", "ui.payload.inbound", "Collect reservation details", 340, 180, {"intent": "resource_reservation_request", "title": "Request infrastructure", "schema": {"fields": [{"key": "resource_id", "label": "Resource", "type": "resource", "required": True}, {"key": "requested_by", "label": "Requested by", "type": "email", "required": True}, {"key": "starts_at", "label": "Starts at", "type": "datetime", "required": True}, {"key": "ends_at", "label": "Ends at", "type": "datetime", "required": True}]}, "timeout_minutes": 1440}),
                node("approval", "hitl.approval", "Approve reservation", 650, 180, {"title": "Infrastructure approval", "message": "Review resource availability and requester policy.", "approver_email": "infrastructure-approvers@example.com", "notify": False}),
                node("book", "resource.book", "Reserve resource", 960, 100, {"resource_id": "{{nodes.collect.resource_id}}", "requested_by": "{{nodes.collect.requested_by}}", "starts_at": "{{nodes.collect.starts_at}}", "ends_at": "{{nodes.collect.ends_at}}", "purpose": "Approved infrastructure allocation"}),
                node("confirm", "ui.payload.outbound", "Publish confirmation", 1260, 100, {"intent": "reservation_confirmed", "title": "Reservation confirmed", "payload": {"booking": "{{nodes.book}}"}}),
                node("reject", "ui.payload.outbound", "Publish rejection", 960, 300, {"intent": "reservation_rejected", "title": "Reservation rejected", "payload": {"message": "The request was not approved."}}),
            ],
            [edge("r1", "start", "collect"), edge("r2", "collect", "approval"), edge("r3", "approval", "book", "approved"), edge("r4", "book", "confirm"), edge("r5", "approval", "reject", "rejected")],
        )

        ad_graph = graph(
            [
                node("start", "trigger.manual", "Start onboarding", 60, 180, {}),
                node("collect", "ui.payload.inbound", "Collect employee details", 330, 180, {"intent": "employee_onboarding", "title": "New employee account", "schema": {"fields": [{"key": "username", "label": "Username", "type": "text", "required": True}, {"key": "display_name", "label": "Display name", "type": "text", "required": True}, {"key": "email", "label": "Email", "type": "email", "required": True}, {"key": "department", "label": "Department", "type": "text", "required": True}]}, "timeout_minutes": 1440}),
                node("validate", "ad.search_user", "Validate directory identity", 620, 180, {"credential_ref": "demo_cred_ad", "query": "{{nodes.collect.username}}"}),
                node("approve", "hitl.approval", "Manager approval", 910, 180, {"title": "Approve employee account", "message": "Confirm employee identity and requested access.", "approver_email": "manager@example.com", "notify": False}),
                node("create", "ad.create_user", "Create AD user", 1200, 100, {"credential_ref": "demo_cred_ad", "username": "{{nodes.collect.username}}", "display_name": "{{nodes.collect.display_name}}", "email": "{{nodes.collect.email}}", "target_ou": "OU=ProvisionedUsers,DC=corp,DC=example", "execute": False}),
                node("result", "ui.payload.outbound", "Publish onboarding result", 1490, 100, {"intent": "employee_onboarding_complete", "title": "Employee account prepared", "payload": {"user": "{{nodes.create}}"}}),
            ],
            [edge("a1", "start", "collect"), edge("a2", "collect", "validate"), edge("a3", "validate", "approve"), edge("a4", "approve", "create", "approved"), edge("a5", "create", "result")],
        )

        gpu_graph = graph(
            [
                node("start", "trigger.manual", "Start GPU maintenance", 50, 180, {}),
                node("select", "resource.search", "Find GPU hosts", 320, 180, {"resource_type": "gpu_server", "status": "available", "tags": ["gpu"]}),
                node("inspect", "gpu.inspect", "Inspect NVIDIA stack", 590, 180, {"resource_id": "{{input.resource_id}}", "execute": False}),
                node("approval", "hitl.approval", "Approve maintenance", 860, 180, {"title": "Approve GPU maintenance", "message": "Review target versions and reboot requirements.", "approver_email": "gpu-operations@example.com", "notify": False}),
                node("update", "gpu.provision", "Update GPU software", 1140, 100, {"resource_id": "{{input.resource_id}}", "driver": "latest_compatible", "cuda": "latest_compatible", "container_toolkit": True, "resolve_nouveau": True, "enable_iommu": False, "allow_reboot": True, "execute": False}),
                node("report", "ui.payload.outbound", "Publish fleet report", 1430, 100, {"intent": "gpu_maintenance_report", "title": "GPU maintenance completed", "payload": {"result": "{{nodes.update}}"}}),
            ],
            [edge("g1", "start", "select"), edge("g2", "select", "inspect"), edge("g3", "inspect", "approval"), edge("g4", "approval", "update", "approved"), edge("g5", "update", "report")],
        )

        vm_graph = graph(
            [
                node("start", "trigger.manual", "Start VM request", 60, 180, {}),
                node("collect", "ui.payload.inbound", "Collect VM requirements", 340, 180, {"intent": "vm_request", "title": "Request a virtual machine", "schema": {"fields": [{"key": "cpu", "label": "CPU cores", "type": "number", "required": True}, {"key": "memory_gb", "label": "Memory", "type": "number", "required": True}, {"key": "operating_system", "label": "Operating system", "type": "select", "options": ["Ubuntu 24.04", "RHEL 9", "Windows Server 2025"], "required": True}]}, "timeout_minutes": 1440}),
                node("approval", "hitl.approval", "Approve capacity", 650, 180, {"title": "Approve VM capacity", "message": "Confirm quota and requested configuration.", "approver_email": "platform-team@example.com", "notify": False}),
                node("api", "http.request", "Provision through virtualisation API", 960, 100, {"method": "POST", "url": "https://virtualisation.example/api/v1/vms", "headers": {}, "body": {"cpu": "{{nodes.collect.cpu}}", "memory_gb": "{{nodes.collect.memory_gb}}", "operating_system": "{{nodes.collect.operating_system}}"}, "execute": False}),
                node("result", "ui.payload.outbound", "Publish VM details", 1260, 100, {"intent": "vm_provisioned", "title": "Virtual machine ready", "payload": {"vm": "{{nodes.api}}"}}),
            ],
            [edge("v1", "start", "collect"), edge("v2", "collect", "approval"), edge("v3", "approval", "api", "approved"), edge("v4", "api", "result")],
        )

        workflows = [
            Workflow(id="demo_wf_resource", name="Infrastructure Reservation", description="Validate a requester, obtain approval, prevent booking conflicts and reserve shared infrastructure.", status="active", current_version=4, graph_json=resource_graph, settings_json={"execution_mode": "durable", "demo": True}, created_by=ADMIN_EMAIL, created_at=now - timedelta(days=18), updated_at=now - timedelta(hours=2)),
            Workflow(id="demo_wf_ad", name="AD Employee Onboarding", description="Collect employee information, validate identity, request approval and prepare an Active Directory account.", status="active", current_version=6, graph_json=ad_graph, settings_json={"execution_mode": "durable", "demo": True}, created_by=ADMIN_EMAIL, created_at=now - timedelta(days=16), updated_at=now - timedelta(minutes=50)),
            Workflow(id="demo_wf_gpu", name="GPU Fleet Maintenance", description="Inspect GPU hosts, approve a maintenance plan and update NVIDIA drivers, CUDA and container support.", status="active", current_version=8, graph_json=gpu_graph, settings_json={"execution_mode": "durable", "plan_mode": True, "demo": True}, created_by=ADMIN_EMAIL, created_at=now - timedelta(days=14), updated_at=now - timedelta(minutes=24)),
            Workflow(id="demo_wf_vm", name="Virtual Machine Provisioning", description="Turn a capacity request into an approved virtual machine provisioning workflow.", status="active", current_version=3, graph_json=vm_graph, settings_json={"execution_mode": "durable", "plan_mode": True, "demo": True}, created_by=ADMIN_EMAIL, created_at=now - timedelta(days=10), updated_at=now - timedelta(hours=5)),
        ]
        db.session.add_all(workflows)

        sandboxes = [
            Sandbox(id="demo_sbx_identity", name="Identity Services", slug="identity-services", description="AD-oriented onboarding, account validation and access workflows.", status="active", environment="production", workflow_ids_json=["demo_wf_ad"], settings_json={"ui_mode": "headless", "allow_external_agents": True, "demo": True}, interface_manifest_json={"interfaces": [{"workflow_id": "demo_wf_ad", "block_id": "collect", "direction": "inbound", "intent": "employee_onboarding"}, {"workflow_id": "demo_wf_ad", "block_id": "result", "direction": "outbound", "intent": "employee_onboarding_complete"}], "event_stream": "/api/v1/sandboxes/demo_sbx_identity/events"}, created_at=now - timedelta(days=12), updated_at=now - timedelta(minutes=40)),
            Sandbox(id="demo_sbx_gpu", name="GPU Operations", slug="gpu-operations", description="Controlled GPU inspection and fleet maintenance across shared compute.", status="active", environment="production", workflow_ids_json=["demo_wf_gpu"], settings_json={"ui_mode": "headless", "allow_external_agents": True, "maintenance_approval_required": True, "demo": True}, interface_manifest_json={"interfaces": [{"workflow_id": "demo_wf_gpu", "block_id": "approval", "direction": "bidirectional", "intent": "gpu_maintenance_approval"}, {"workflow_id": "demo_wf_gpu", "block_id": "report", "direction": "outbound", "intent": "gpu_maintenance_report"}], "event_stream": "/api/v1/sandboxes/demo_sbx_gpu/events"}, created_at=now - timedelta(days=11), updated_at=now - timedelta(minutes=22)),
            Sandbox(id="demo_sbx_platform", name="Infrastructure Service Desk", slug="infrastructure-service-desk", description="Resource reservation and virtual machine delivery for engineering teams.", status="active", environment="staging", workflow_ids_json=["demo_wf_resource", "demo_wf_vm"], settings_json={"ui_mode": "headless", "allow_external_agents": True, "demo": True}, interface_manifest_json={"interfaces": [{"workflow_id": "demo_wf_resource", "block_id": "collect", "direction": "inbound", "intent": "resource_reservation_request"}, {"workflow_id": "demo_wf_vm", "block_id": "collect", "direction": "inbound", "intent": "vm_request"}], "event_stream": "/api/v1/sandboxes/demo_sbx_platform/events"}, created_at=now - timedelta(days=9), updated_at=now - timedelta(hours=1)),
        ]
        db.session.add_all(sandboxes)

        attachments = [
            SandboxAttachment(id="demo_att_portal", sandbox_id="demo_sbx_platform", name="Engineering Service Portal", attachment_type="frontend", provider="react", status="active", credential_ref=None, config_json={"mode": "byoui", "base_path": "/infrastructure"}, scopes_json=["sandbox.manifest.read", "sandbox.events.read", "ui_transaction.respond"], created_at=now - timedelta(days=8), updated_at=now - timedelta(days=1)),
            SandboxAttachment(id="demo_att_claude", sandbox_id="demo_sbx_gpu", name="GPU Operations Agent", attachment_type="agent", provider="anthropic", status="active", credential_ref=None, config_json={"mode": "byok", "role": "maintenance_assistant"}, scopes_json=["sandbox.manifest.read", "sandbox.events.read", "execution.read"], created_at=now - timedelta(days=7), updated_at=now - timedelta(hours=3)),
            SandboxAttachment(id="demo_att_codex", sandbox_id="demo_sbx_identity", name="Identity UI Builder", attachment_type="agent", provider="openai", status="active", credential_ref=None, config_json={"mode": "byok", "role": "frontend_builder"}, scopes_json=["sandbox.manifest.read", "ui_payload.read"], created_at=now - timedelta(days=6), updated_at=now - timedelta(hours=4)),
        ]
        db.session.add_all(attachments)

        bookings = [
            Booking(id="demo_book_active", resource_id="demo_res_esxi_01", requested_by="platform.engineering@example.com", purpose="Quarterly virtualisation validation", starts_at=now - timedelta(hours=2), ends_at=now + timedelta(hours=6), status="active", metadata_json={"environment": "demo_sbx_platform", "demo": True}, created_at=now - timedelta(days=2), updated_at=now - timedelta(hours=2)),
            Booking(id="demo_book_gpu", resource_id="demo_res_gpu_01", requested_by="ai.research@example.com", purpose="Distributed model training", starts_at=now + timedelta(hours=4), ends_at=now + timedelta(hours=12), status="confirmed", metadata_json={"approval": "approved", "demo": True}, created_at=now - timedelta(hours=18), updated_at=now - timedelta(hours=16)),
            Booking(id="demo_book_namespace", resource_id="demo_res_namespace_01", requested_by="training.team@example.com", purpose="GPU infrastructure workshop", starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=1, hours=6), status="confirmed", metadata_json={"demo": True}, created_at=now - timedelta(hours=10), updated_at=now - timedelta(hours=9)),
            Booking(id="demo_book_completed", resource_id="demo_res_vm_01", requested_by="qa.team@example.com", purpose="Release validation", starts_at=now - timedelta(days=2), ends_at=now - timedelta(days=1, hours=20), status="completed", metadata_json={"demo": True}, created_at=now - timedelta(days=3), updated_at=now - timedelta(days=1, hours=20)),
        ]
        db.session.add_all(bookings)

        executions = [
            Execution(id="demo_exec_gpu_running", workflow_id="demo_wf_gpu", sandbox_id="demo_sbx_gpu", status="running", trigger_type="manual", input_json={"resource_id": "demo_res_gpu_02"}, context_json={"current_node": "inspect", "demo": True}, output_json={}, started_at=now - timedelta(minutes=14), completed_at=None, created_at=now - timedelta(minutes=14), updated_at=now - timedelta(minutes=2)),
            Execution(id="demo_exec_ad_waiting", workflow_id="demo_wf_ad", sandbox_id="demo_sbx_identity", status="waiting", trigger_type="ui", input_json={"username": "jdoe", "display_name": "Jordan Doe", "email": "jordan.doe@example.com", "department": "Engineering"}, context_json={"current_node": "approve", "demo": True}, output_json={}, started_at=now - timedelta(minutes=31), completed_at=None, created_at=now - timedelta(minutes=31), updated_at=now - timedelta(minutes=8)),
            Execution(id="demo_exec_booking_completed", workflow_id="demo_wf_resource", sandbox_id="demo_sbx_platform", status="completed", trigger_type="ui", input_json={"resource_id": "demo_res_gpu_01"}, context_json={"demo": True}, output_json={"booking_id": "demo_book_gpu", "status": "confirmed"}, started_at=now - timedelta(hours=3), completed_at=now - timedelta(hours=2, minutes=56), created_at=now - timedelta(hours=3), updated_at=now - timedelta(hours=2, minutes=56)),
            Execution(id="demo_exec_vm_failed", workflow_id="demo_wf_vm", sandbox_id="demo_sbx_platform", status="failed", trigger_type="api", input_json={"cpu": 32, "memory_gb": 128, "operating_system": "RHEL 9"}, context_json={"demo": True}, output_json={}, error="Virtualisation capacity policy rejected the requested memory allocation.", started_at=now - timedelta(hours=5), completed_at=now - timedelta(hours=4, minutes=57), created_at=now - timedelta(hours=5), updated_at=now - timedelta(hours=4, minutes=57)),
            Execution(id="demo_exec_gpu_completed", workflow_id="demo_wf_gpu", sandbox_id="demo_sbx_gpu", status="completed", trigger_type="schedule", input_json={"resource_id": "demo_res_gpu_01"}, context_json={"demo": True}, output_json={"driver_version": "570.172.08", "cuda_version": "12.8", "validation": "passed"}, started_at=now - timedelta(days=1, hours=1), completed_at=now - timedelta(days=1), created_at=now - timedelta(days=1, hours=1), updated_at=now - timedelta(days=1)),
            Execution(id="demo_exec_ad_completed", workflow_id="demo_wf_ad", sandbox_id="demo_sbx_identity", status="completed", trigger_type="ui", input_json={"username": "asmith"}, context_json={"demo": True}, output_json={"username": "asmith", "status": "created", "target_ou": "ProvisionedUsers"}, started_at=now - timedelta(days=1, hours=5), completed_at=now - timedelta(days=1, hours=4, minutes=56), created_at=now - timedelta(days=1, hours=5), updated_at=now - timedelta(days=1, hours=4, minutes=56)),
            Execution(id="demo_exec_booking_waiting", workflow_id="demo_wf_resource", sandbox_id="demo_sbx_platform", status="waiting", trigger_type="ui", input_json={"resource_id": "demo_res_storage_01", "requested_by": "data.platform@example.com"}, context_json={"current_node": "approval", "demo": True}, output_json={}, started_at=now - timedelta(minutes=48), completed_at=None, created_at=now - timedelta(minutes=48), updated_at=now - timedelta(minutes=15)),
            Execution(id="demo_exec_vm_completed", workflow_id="demo_wf_vm", sandbox_id="demo_sbx_platform", status="completed", trigger_type="api", input_json={"cpu": 8, "memory_gb": 32, "operating_system": "Ubuntu 24.04"}, context_json={"demo": True}, output_json={"hostname": "eng-vm-104", "status": "ready"}, started_at=now - timedelta(days=2), completed_at=now - timedelta(days=1, hours=23, minutes=53), created_at=now - timedelta(days=2), updated_at=now - timedelta(days=1, hours=23, minutes=53)),
        ]
        db.session.add_all(executions)

        block_executions = [
            BlockExecution(id="demo_bex_gpu_inspect", execution_id="demo_exec_gpu_running", block_id="inspect", block_type="gpu.inspect", status="running", input_json={"resource_id": "demo_res_gpu_02"}, output_json={"stage": "driver_inventory", "progress": 65}, started_at=now - timedelta(minutes=12), completed_at=None, created_at=now - timedelta(minutes=12), updated_at=now - timedelta(minutes=2)),
            BlockExecution(id="demo_bex_ad_approve", execution_id="demo_exec_ad_waiting", block_id="approve", block_type="hitl.approval", status="waiting", input_json={"username": "jdoe"}, output_json={}, started_at=now - timedelta(minutes=25), completed_at=None, created_at=now - timedelta(minutes=25), updated_at=now - timedelta(minutes=8)),
            BlockExecution(id="demo_bex_booking_done", execution_id="demo_exec_booking_completed", block_id="book", block_type="resource.book", status="completed", input_json={"resource_id": "demo_res_gpu_01"}, output_json={"booking_id": "demo_book_gpu"}, started_at=now - timedelta(hours=2, minutes=59), completed_at=now - timedelta(hours=2, minutes=57), created_at=now - timedelta(hours=2, minutes=59), updated_at=now - timedelta(hours=2, minutes=57)),
        ]
        db.session.add_all(block_executions)

        transactions = [
            UITransaction(id="demo_uitx_ad_approval", execution_id="demo_exec_ad_waiting", sandbox_id="demo_sbx_identity", workflow_id="demo_wf_ad", block_id="approve", direction="bidirectional", status="open", intent="employee_account_approval", schema_json={"fields": [{"key": "department", "label": "Department", "type": "text", "value": "Engineering", "readOnly": True}]}, payload_json={"title": "Approve Jordan Doe", "message": "Confirm identity, department and requested directory access."}, response_json={}, allowed_actions_json=["approve", "reject"], token="demo-token-ad-approval", expires_at=now + timedelta(hours=22), responded_at=None, responded_by=None, created_at=now - timedelta(minutes=25), updated_at=now - timedelta(minutes=8)),
            UITransaction(id="demo_uitx_gpu_approval", execution_id="demo_exec_gpu_running", sandbox_id="demo_sbx_gpu", workflow_id="demo_wf_gpu", block_id="approval", direction="bidirectional", status="open", intent="gpu_maintenance_approval", schema_json={"fields": [{"key": "driver", "label": "Target driver", "type": "text", "value": "latest_compatible", "readOnly": True}, {"key": "allow_reboot", "label": "Allow reboot", "type": "boolean", "value": True}]}, payload_json={"title": "Approve GPU maintenance", "message": "H100-02 requires a driver update and reboot."}, response_json={}, allowed_actions_json=["approve", "reject"], token="demo-token-gpu-approval", expires_at=now + timedelta(hours=4), responded_at=None, responded_by=None, created_at=now - timedelta(minutes=10), updated_at=now - timedelta(minutes=4)),
            UITransaction(id="demo_uitx_storage_approval", execution_id="demo_exec_booking_waiting", sandbox_id="demo_sbx_platform", workflow_id="demo_wf_resource", block_id="approval", direction="bidirectional", status="open", intent="storage_reservation_approval", schema_json={"fields": [{"key": "capacity_tb", "label": "Requested capacity", "type": "number", "value": 20, "readOnly": True}]}, payload_json={"title": "Approve storage allocation", "message": "Data Platform requested 20 TB from the shared AI storage pool."}, response_json={}, allowed_actions_json=["approve", "reject"], token="demo-token-storage-approval", expires_at=now + timedelta(hours=18), responded_at=None, responded_by=None, created_at=now - timedelta(minutes=42), updated_at=now - timedelta(minutes=15)),
            UITransaction(id="demo_uitx_completed", execution_id="demo_exec_booking_completed", sandbox_id="demo_sbx_platform", workflow_id="demo_wf_resource", block_id="approval", direction="bidirectional", status="responded", intent="resource_reservation_approval", schema_json={"fields": []}, payload_json={"title": "Approve GPU reservation"}, response_json={"action": "approve", "values": {}}, allowed_actions_json=["approve", "reject"], token="demo-token-completed", expires_at=now + timedelta(hours=1), responded_at=now - timedelta(hours=2, minutes=58), responded_by=ADMIN_EMAIL, created_at=now - timedelta(hours=3), updated_at=now - timedelta(hours=2, minutes=58)),
        ]
        db.session.add_all(transactions)

        events = [
            ExecutionEvent(execution_id="demo_exec_gpu_running", sandbox_id="demo_sbx_gpu", event_type="execution.started", payload_json={"workflow": "GPU Fleet Maintenance"}, created_at=now - timedelta(minutes=14)),
            ExecutionEvent(execution_id="demo_exec_gpu_running", sandbox_id="demo_sbx_gpu", event_type="block.progress", payload_json={"block_id": "inspect", "stage": "driver_inventory", "progress": 65}, created_at=now - timedelta(minutes=2)),
            ExecutionEvent(execution_id="demo_exec_ad_waiting", sandbox_id="demo_sbx_identity", event_type="interaction.required", payload_json={"transaction_id": "demo_uitx_ad_approval"}, created_at=now - timedelta(minutes=25)),
            ExecutionEvent(execution_id="demo_exec_booking_completed", sandbox_id="demo_sbx_platform", event_type="execution.completed", payload_json={"booking_id": "demo_book_gpu"}, created_at=now - timedelta(hours=2, minutes=56)),
        ]
        db.session.add_all(events)

        audits = [
            AuditEvent(id="demo_audit_01", actor=ADMIN_EMAIL, action="workflow.published", target_type="workflow", target_id="demo_wf_gpu", payload_json={"version": 8}, created_at=now - timedelta(minutes=24)),
            AuditEvent(id="demo_audit_02", actor="gpu-operations@example.com", action="gpu.inspection.started", target_type="resource", target_id="demo_res_gpu_02", payload_json={"execution_id": "demo_exec_gpu_running"}, created_at=now - timedelta(minutes=14)),
            AuditEvent(id="demo_audit_03", actor="manager@example.com", action="ui_transaction.opened", target_type="ui_transaction", target_id="demo_uitx_ad_approval", payload_json={"workflow": "AD Employee Onboarding"}, created_at=now - timedelta(minutes=25)),
            AuditEvent(id="demo_audit_04", actor=ADMIN_EMAIL, action="booking.created", target_type="booking", target_id="demo_book_gpu", payload_json={"resource_id": "demo_res_gpu_01"}, created_at=now - timedelta(hours=18)),
            AuditEvent(id="demo_audit_05", actor="codex-agent", action="sandbox_attachment.connected", target_type="sandbox", target_id="demo_sbx_identity", payload_json={"attachment": "Identity UI Builder", "mode": "byok"}, created_at=now - timedelta(hours=4)),
        ]
        db.session.add_all(audits)

        db.session.commit()
        print("InfraRelay demo data created.")
        print("Dashboard: 4 automations, 3 environments, 6 resources, 3 open requests, 3 active/waiting runs, 3 active reservations.")
        print("All seeded records use the 'demo_' ID prefix and can be removed safely.")


if __name__ == "__main__":
    main()
