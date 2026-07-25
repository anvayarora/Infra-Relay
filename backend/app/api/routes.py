from __future__ import annotations
import json
import re
import time
from datetime import datetime, timezone
from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, verify_jwt_in_request
from sqlalchemy import desc
from ..audit import audit
from ..blocks import DEFINITIONS, serialize_definition
from ..config import config
from ..engine import runtime, serialize_booking, serialize_resource
from ..extensions import db
from ..models import AuditEvent, BlockExecution, Booking, CredentialReference, Execution, ExecutionEvent, Resource, Sandbox, SandboxAttachment, UITransaction, User, Workflow, utcnow
from ..resource_types import ResourceType
from ..security import secret_box

api = Blueprint("api", __name__, url_prefix="/api/v1")

def body() -> dict:
    return request.get_json(silent=True) or {}

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def workflow_json(item: Workflow, include_graph: bool = True):
    data = {"id":item.id,"name":item.name,"description":item.description,"status":item.status,"current_version":item.current_version,"settings":item.settings_json or {},"created_by":item.created_by,"created_at":item.created_at.isoformat(),"updated_at":item.updated_at.isoformat()}
    if include_graph:
        data["graph"] = item.graph_json or {"nodes":[],"edges":[]}
    return data

def sandbox_json(item: Sandbox):
    return {"id":item.id,"name":item.name,"slug":item.slug,"description":item.description,"status":item.status,"environment":item.environment,"workflow_ids":item.workflow_ids_json or [],"settings":item.settings_json or {},"interface_manifest":item.interface_manifest_json or {},"created_at":item.created_at.isoformat(),"updated_at":item.updated_at.isoformat()}

def execution_json(item: Execution, details: bool = False):
    data = {"id":item.id,"workflow_id":item.workflow_id,"workflow_name":item.workflow.name if item.workflow else None,"sandbox_id":item.sandbox_id,"sandbox_name":item.sandbox.name if item.sandbox else None,"status":item.status,"trigger_type":item.trigger_type,"input":item.input_json or {},"output":item.output_json or {},"error":item.error,"started_at":item.started_at.isoformat() if item.started_at else None,"completed_at":item.completed_at.isoformat() if item.completed_at else None,"created_at":item.created_at.isoformat(),"updated_at":item.updated_at.isoformat()}
    if details:
        data["context"] = item.context_json or {}
        data["blocks"] = [{"id":b.id,"block_id":b.block_id,"block_type":b.block_type,"status":b.status,"input":b.input_json or {},"output":b.output_json or {},"error":b.error,"started_at":b.started_at.isoformat() if b.started_at else None,"completed_at":b.completed_at.isoformat() if b.completed_at else None} for b in BlockExecution.query.filter_by(execution_id=item.id).order_by(BlockExecution.created_at).all()]
    return data

def transaction_json(item: UITransaction, include_token: bool = False):
    data = {"id":item.id,"execution_id":item.execution_id,"sandbox_id":item.sandbox_id,"workflow_id":item.workflow_id,"block_id":item.block_id,"direction":item.direction,"status":item.status,"intent":item.intent,"schema":item.schema_json or {},"payload":item.payload_json or {},"response":item.response_json or {},"allowed_actions":item.allowed_actions_json or [],"expires_at":item.expires_at.isoformat() if item.expires_at else None,"responded_at":item.responded_at.isoformat() if item.responded_at else None,"responded_by":item.responded_by,"created_at":item.created_at.isoformat()}
    if include_token:
        data["token"] = item.token
    return data

@api.get("/health")
def health():
    return {"status":"ok","service":"infrarelay","time":utcnow().isoformat()}

@api.post("/auth/login")
def login():
    data = body()
    email = str(data.get("email") or "admin@infrarelay.local").lower()
    if not config.allow_demo_auth:
        return {"error":"Demo authentication is disabled. Configure SSO/OIDC for production."}, 403
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=data.get("name") or email.split("@")[0].replace(".", " ").title(), role="admin")
        db.session.add(user)
        db.session.commit()
    token = create_access_token(identity=user.email, additional_claims={"role":user.role,"name":user.name})
    return {"access_token":token,"user":{"id":user.id,"email":user.email,"name":user.name,"role":user.role}}

@api.get("/auth/me")
@jwt_required()
def me():
    user = User.query.filter_by(email=get_jwt_identity()).first()
    return {"user":{"id":user.id,"email":user.email,"name":user.name,"role":user.role}}

@api.get("/blocks")
@jwt_required()
def blocks():
    return {"items":[serialize_definition(item) for item in DEFINITIONS]}

@api.get("/dashboard")
@jwt_required()
def dashboard():
    return {"metrics":{
        "workflows":Workflow.query.count(),"sandboxes":Sandbox.query.count(),"resources":Resource.query.count(),"open_transactions":UITransaction.query.filter_by(status="open").count(),
        "running_executions":Execution.query.filter(Execution.status.in_(["queued","running","waiting"])).count(),"bookings":Booking.query.filter(Booking.status.in_(["confirmed","active"])).count(),
    },"recent_executions":[execution_json(item) for item in Execution.query.order_by(desc(Execution.created_at)).limit(8).all()],"open_transactions":[transaction_json(item) for item in UITransaction.query.filter_by(status="open").order_by(desc(UITransaction.created_at)).limit(6).all()]}

@api.get("/workflows")
@jwt_required()
def list_workflows():
    return {"items":[workflow_json(item, False) for item in Workflow.query.order_by(desc(Workflow.updated_at)).all()]}

@api.post("/workflows")
@jwt_required()
def create_workflow():
    data = body()
    item = Workflow(name=data.get("name") or "Untitled workflow", description=data.get("description") or "", graph_json=data.get("graph") or {"nodes":[],"edges":[]}, settings_json=data.get("settings") or {}, created_by=get_jwt_identity())
    db.session.add(item); db.session.commit(); audit(get_jwt_identity(), "workflow.created", "workflow", item.id, {"name":item.name})
    return workflow_json(item), 201

@api.get("/workflows/<workflow_id>")
@jwt_required()
def get_workflow(workflow_id):
    item = db.get_or_404(Workflow, workflow_id)
    return workflow_json(item)

@api.put("/workflows/<workflow_id>")
@jwt_required()
def update_workflow(workflow_id):
    item = db.get_or_404(Workflow, workflow_id); data = body()
    for key in ["name","description","status"]:
        if key in data: setattr(item, key, data[key])
    if "graph" in data: item.graph_json = data["graph"]
    if "settings" in data: item.settings_json = data["settings"]
    item.current_version += 1
    db.session.commit(); audit(get_jwt_identity(), "workflow.updated", "workflow", item.id, {"version":item.current_version})
    return workflow_json(item)

@api.delete("/workflows/<workflow_id>")
@jwt_required()
def delete_workflow(workflow_id):
    item = db.get_or_404(Workflow, workflow_id)
    if Execution.query.filter_by(workflow_id=item.id).first():
        item.status = "archived"; db.session.commit()
    else:
        db.session.delete(item); db.session.commit()
    audit(get_jwt_identity(), "workflow.archived", "workflow", workflow_id)
    return {"ok":True}

@api.post("/workflows/<workflow_id>/validate")
@jwt_required()
def validate_workflow(workflow_id):
    item = db.get_or_404(Workflow, workflow_id); graph = item.graph_json or {}; nodes = graph.get("nodes", []); edges = graph.get("edges", [])
    errors=[]; warnings=[]; ids={node.get("id") for node in nodes}
    if not nodes: errors.append("Workflow has no blocks")
    if not any(node.get("type","").startswith("trigger.") or node.get("type") == "ui.payload.inbound" for node in nodes): warnings.append("Workflow has no explicit trigger or UI inbound entrypoint")
    for edge in edges:
        if edge.get("source") not in ids or edge.get("target") not in ids: errors.append(f"Edge {edge.get('id')} references a missing block")
    return {"valid":not errors,"errors":errors,"warnings":warnings,"summary":{"nodes":len(nodes),"edges":len(edges)}}

@api.post("/workflows/<workflow_id>/execute")
@jwt_required()
def execute_workflow(workflow_id):
    workflow = db.get_or_404(Workflow, workflow_id); data=body()
    item = Execution(workflow_id=workflow.id, sandbox_id=data.get("sandbox_id"), trigger_type=data.get("trigger_type") or "manual", input_json=data.get("input") or {}, context_json={"input":data.get("input") or {},"nodes":{},"responses":{},"completed":[],"queue":[]})
    db.session.add(item); db.session.commit(); audit(get_jwt_identity(), "execution.created", "execution", item.id, {"workflow_id":workflow.id})
    runtime.submit(item.id)
    return execution_json(item), 202

@api.get("/sandboxes")
@jwt_required()
def list_sandboxes():
    return {"items":[sandbox_json(item) for item in Sandbox.query.order_by(desc(Sandbox.updated_at)).all()]}

@api.post("/sandboxes")
@jwt_required()
def create_sandbox():
    data=body(); name=data.get("name") or "New sandbox"; slug=data.get("slug") or slugify(name)
    if Sandbox.query.filter_by(slug=slug).first(): slug=f"{slug}-{int(time.time())}"
    item=Sandbox(name=name,slug=slug,description=data.get("description") or "",environment=data.get("environment") or "development",workflow_ids_json=data.get("workflow_ids") or [],settings_json=data.get("settings") or {})
    db.session.add(item); db.session.commit(); _refresh_manifest(item); audit(get_jwt_identity(), "sandbox.created", "sandbox", item.id, {"slug":slug})
    return sandbox_json(item),201

@api.get("/sandboxes/<sandbox_id>")
@jwt_required()
def get_sandbox(sandbox_id): return sandbox_json(db.get_or_404(Sandbox,sandbox_id))

@api.put("/sandboxes/<sandbox_id>")
@jwt_required()
def update_sandbox(sandbox_id):
    item=db.get_or_404(Sandbox,sandbox_id); data=body()
    for key in ["name","description","status","environment"]:
        if key in data: setattr(item,key,data[key])
    if "workflow_ids" in data: item.workflow_ids_json=data["workflow_ids"]
    if "settings" in data: item.settings_json=data["settings"]
    db.session.commit(); _refresh_manifest(item); audit(get_jwt_identity(), "sandbox.updated", "sandbox", item.id)
    return sandbox_json(item)

def _refresh_manifest(item: Sandbox):
    workflows=Workflow.query.filter(Workflow.id.in_(item.workflow_ids_json or ["__none__"])).all()
    interfaces=[]
    for workflow in workflows:
        for node in (workflow.graph_json or {}).get("nodes",[]):
            if node.get("type","").startswith("ui.payload"):
                settings=(node.get("data") or {}).get("settings") or {}
                interfaces.append({"workflow_id":workflow.id,"workflow_name":workflow.name,"block_id":node["id"],"direction":node["type"].split(".")[-1],"intent":settings.get("intent"),"schema":settings.get("schema") or {}})
    item.interface_manifest_json={"sandbox_id":item.id,"slug":item.slug,"version":item.updated_at.isoformat(),"interfaces":interfaces,"event_stream":f"/api/v1/sandboxes/{item.id}/events","transactions":"/api/v1/ui-transactions"}
    db.session.commit()

@api.get("/sandboxes/<sandbox_id>/events")
@jwt_required()
def sandbox_events(sandbox_id):
    db.get_or_404(Sandbox,sandbox_id); last_id=int(request.args.get("after",request.headers.get("Last-Event-ID","0")) or 0)
    @stream_with_context
    def stream():
        nonlocal last_id
        heartbeat=0
        while True:
            rows=ExecutionEvent.query.filter(ExecutionEvent.sandbox_id==sandbox_id,ExecutionEvent.id>last_id).order_by(ExecutionEvent.id).limit(100).all()
            if rows:
                for row in rows:
                    last_id=row.id
                    yield f"id: {row.id}\nevent: {row.event_type}\ndata: {json.dumps({'id':row.id,'execution_id':row.execution_id,'type':row.event_type,'payload':row.payload_json,'created_at':row.created_at.isoformat()})}\n\n"
            else:
                heartbeat+=1
                yield f": heartbeat {heartbeat}\n\n"
            time.sleep(2)
    return Response(stream(),mimetype="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@api.get("/sandboxes/<sandbox_id>/manifest")
@jwt_required()
def sandbox_manifest(sandbox_id):
    item=db.get_or_404(Sandbox,sandbox_id)
    return item.interface_manifest_json or {}

@api.get("/sandboxes/<sandbox_id>/developer-kit")
@jwt_required()
def sandbox_developer_kit(sandbox_id):
    item = db.get_or_404(Sandbox, sandbox_id)
    workflows = Workflow.query.filter(Workflow.id.in_(item.workflow_ids_json or ["__none__"])).all()
    manifest = item.interface_manifest_json or {}
    return {
        "sandbox": sandbox_json(item),
        "manifest": manifest,
        "workflows": [workflow_json(workflow) for workflow in workflows],
        "block_registry": [serialize_definition(definition) for definition in DEFINITIONS],
        "integration": {
            "manifest": f"/api/v1/sandboxes/{item.id}/manifest",
            "event_stream": f"/api/v1/sandboxes/{item.id}/events",
            "execute": f"/api/v1/sandboxes/{item.id}/execute",
            "respond": "/api/v1/ui-transactions/{transaction_id}/respond",
            "typescript_sdk": "sdk/typescript/src/index.ts",
        },
        "agent_brief": (
            f"Build a customer-owned frontend for the InfraRelay sandbox '{item.name}'. "
            "Use the supplied manifest as the source of truth. Render inbound and bidirectional "
            "transactions with the customer's design system, subscribe to the SSE event stream, "
            "submit actions through the transaction response endpoint, and never embed infrastructure "
            "credentials in frontend code. Preserve every field key and allowed action exactly."
        ),
    }

@api.post("/sandboxes/<sandbox_id>/execute")
@jwt_required()
def execute_sandbox(sandbox_id):
    sandbox=db.get_or_404(Sandbox,sandbox_id); data=body()
    workflow_id=data.get("workflow_id") or ((sandbox.workflow_ids_json or [None])[0])
    if not workflow_id or workflow_id not in (sandbox.workflow_ids_json or []): return {"error":"Select a workflow deployed to this sandbox"},422
    workflow=db.get_or_404(Workflow,workflow_id)
    item=Execution(workflow_id=workflow.id,sandbox_id=sandbox.id,trigger_type=data.get("trigger_type") or "sandbox_api",input_json=data.get("input") or {},context_json={"input":data.get("input") or {},"nodes":{},"responses":{},"completed":[],"queue":[]})
    db.session.add(item);db.session.commit();audit(get_jwt_identity(),"sandbox.execution.created","execution",item.id,{"sandbox_id":sandbox.id,"workflow_id":workflow.id});runtime.submit(item.id)
    return execution_json(item),202

@api.get("/sandboxes/<sandbox_id>/attachments")
@jwt_required()
def list_attachments(sandbox_id):
    db.get_or_404(Sandbox,sandbox_id)
    items=SandboxAttachment.query.filter_by(sandbox_id=sandbox_id).order_by(desc(SandboxAttachment.created_at)).all()
    return {"items":[{"id":x.id,"sandbox_id":x.sandbox_id,"name":x.name,"attachment_type":x.attachment_type,"provider":x.provider,"status":x.status,"credential_ref":x.credential_ref,"config":x.config_json or {},"scopes":x.scopes_json or [],"created_at":x.created_at.isoformat()} for x in items]}

@api.post("/sandboxes/<sandbox_id>/attachments")
@jwt_required()
def create_attachment(sandbox_id):
    db.get_or_404(Sandbox,sandbox_id); data=body()
    item=SandboxAttachment(sandbox_id=sandbox_id,name=data.get("name") or "Unnamed attachment",attachment_type=data.get("attachment_type") or "frontend",provider=data.get("provider") or "custom",credential_ref=data.get("credential_ref"),config_json=data.get("config") or {},scopes_json=data.get("scopes") or ["sandbox.manifest.read","sandbox.events.read","ui_transaction.respond"])
    db.session.add(item);db.session.commit();audit(get_jwt_identity(),"sandbox_attachment.created","sandbox_attachment",item.id,{"sandbox_id":sandbox_id,"type":item.attachment_type,"provider":item.provider})
    return {"id":item.id,"sandbox_id":item.sandbox_id,"name":item.name,"attachment_type":item.attachment_type,"provider":item.provider,"status":item.status,"credential_ref":item.credential_ref,"config":item.config_json,"scopes":item.scopes_json},201

@api.delete("/sandboxes/<sandbox_id>/attachments/<attachment_id>")
@jwt_required()
def delete_attachment(sandbox_id,attachment_id):
    item=db.get_or_404(SandboxAttachment,attachment_id)
    if item.sandbox_id!=sandbox_id:return {"error":"Attachment does not belong to this sandbox"},409
    item.status="disabled";db.session.commit();audit(get_jwt_identity(),"sandbox_attachment.disabled","sandbox_attachment",item.id)
    return {"ok":True}

@api.get("/executions")
@jwt_required()
def list_executions():
    query=Execution.query
    if request.args.get("sandbox_id"): query=query.filter_by(sandbox_id=request.args["sandbox_id"])
    if request.args.get("status"): query=query.filter_by(status=request.args["status"])
    return {"items":[execution_json(item) for item in query.order_by(desc(Execution.created_at)).limit(200).all()]}

@api.get("/executions/<execution_id>")
@jwt_required()
def get_execution(execution_id): return execution_json(db.get_or_404(Execution,execution_id),True)

@api.get("/executions/<execution_id>/events")
@jwt_required()
def execution_events(execution_id):
    db.get_or_404(Execution,execution_id)
    rows=ExecutionEvent.query.filter_by(execution_id=execution_id).order_by(ExecutionEvent.id).all()
    return {"items":[{"id":r.id,"type":r.event_type,"payload":r.payload_json,"created_at":r.created_at.isoformat()} for r in rows]}

@api.get("/ui-transactions")
@jwt_required()
def list_transactions():
    query=UITransaction.query
    if request.args.get("status"): query=query.filter_by(status=request.args["status"])
    return {"items":[transaction_json(item,True) for item in query.order_by(desc(UITransaction.created_at)).limit(200).all()]}

@api.get("/ui-transactions/<transaction_id>")
def get_transaction(transaction_id):
    item = db.get_or_404(UITransaction, transaction_id)
    token = request.args.get("token") or request.headers.get("X-Transaction-Token")
    verify_jwt_in_request(optional=True)
    identity = get_jwt_identity()
    if not identity and token != item.token:
        return {"error": "A valid transaction token is required"}, 401
    return transaction_json(item)

@api.post("/ui-transactions/<transaction_id>/respond")
def respond_transaction(transaction_id):
    item=db.get_or_404(UITransaction,transaction_id); data=body(); token=data.get("token") or request.headers.get("X-Transaction-Token")
    actor="external-ui"
    try:
        verify_jwt_in_request(optional=True)
        actor = get_jwt_identity() or actor
    except Exception:
        pass
    if not actor or actor=="external-ui":
        if token != item.token: return {"error":"A valid transaction token is required"},401
    if item.status != "open": return {"error":"Transaction is no longer open"},409
    if item.expires_at:
        expires_at = item.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            item.status = "expired"
            db.session.commit()
            return {"error": "Transaction has expired"}, 410
    action=data.get("action") or "submit"
    if item.allowed_actions_json and action not in item.allowed_actions_json: return {"error":f"Action must be one of {item.allowed_actions_json}"},422
    item.status="responded"; item.response_json={"action":action,"values":data.get("values") or {}}; item.responded_at=utcnow(); item.responded_by=actor
    execution=db.session.get(Execution,item.execution_id); context=execution.context_json or {}; context.setdefault("responses",{})[item.block_id]=item.response_json; execution.context_json=context; execution.status="queued"
    waiting=BlockExecution.query.filter_by(execution_id=execution.id,block_id=item.block_id,status="waiting").first()
    if waiting: waiting.status="running"
    db.session.commit(); audit(actor,"ui_transaction.responded","ui_transaction",item.id,{"action":action}); runtime.submit(execution.id)
    return transaction_json(item),202

@api.get("/resources")
@jwt_required()
def list_resources():
    query=Resource.query
    if request.args.get("type"): query=query.filter_by(resource_type=request.args["type"])
    if request.args.get("status"): query=query.filter_by(status=request.args["status"])
    return {"items":[serialize_resource(item) for item in query.order_by(Resource.name).all()]}

@api.post("/resources")
@jwt_required()
def create_resource():
    data = body()

    resource_type = (
        data.get("resource_type")
        or ""
    )

    type_definition = (
        ResourceType.query
        .filter_by(
            key=resource_type,
            active=True,
        )
        .first()
    )

    if not type_definition:
        return {
            "error":
                "Create or select a "
                "valid resource type "
                "first"
        }, 422

    capabilities = (
        data.get("capabilities")
        or {}
    )

    missing = [
        field.get("label")
        or field.get("key")
        for field in (
            type_definition
            .fields_json
            or []
        )
        if field.get("required")
        and (
            field.get("key")
            not in capabilities
            or capabilities.get(
                field.get("key")
            )
            in (
                None,
                "",
            )
        )
    ]

    if missing:
        return {
            "error":
                "Complete the required "
                "fields: "
                + ", ".join(missing)
        }, 422

    booking_policy = dict(
        type_definition
        .booking_defaults_json
        or {}
    )

    booking_policy.update(
        data.get("booking_policy")
        or {}
    )

    item = Resource(
        name=(
            data.get("name")
            or "Unnamed resource"
        ),
        resource_type=resource_type,
        status=(
            data.get("status")
            or "available"
        ),
        location=(
            data.get("location")
            or ""
        ),
        connection_ref=(
            data.get(
                "connection_ref"
            )
        ),
        capabilities_json=(
            capabilities
        ),
        booking_policy_json=(
            booking_policy
        ),
        maintenance_json=(
            data.get("maintenance")
            or {}
        ),
        tags_json=(
            data.get("tags")
            or []
        ),
    )

    db.session.add(item)
    db.session.commit()

    audit(
        get_jwt_identity(),
        "resource.created",
        "resource",
        item.id,
        {
            "name": item.name,
            "resource_type":
                resource_type,
        },
    )

    return (
        serialize_resource(item),
        201,
    )

@api.get("/resources/<resource_id>")
@jwt_required()
def get_resource(resource_id): return serialize_resource(db.get_or_404(Resource,resource_id))

@api.put("/resources/<resource_id>")
@jwt_required()
def update_resource(resource_id):
    item=db.get_or_404(Resource,resource_id);data=body()
    mapping={"name":"name","resource_type":"resource_type","status":"status","location":"location","connection_ref":"connection_ref","capabilities":"capabilities_json","booking_policy":"booking_policy_json","maintenance":"maintenance_json","tags":"tags_json"}
    for key,attr in mapping.items():
        if key in data:setattr(item,attr,data[key])
    db.session.commit();audit(get_jwt_identity(),"resource.updated","resource",item.id);return serialize_resource(item)

@api.delete("/resources/<resource_id>")
@jwt_required()
def delete_resource(resource_id):
    item=db.get_or_404(Resource,resource_id)
    if Booking.query.filter_by(resource_id=item.id).first(): item.status="retired"
    else: db.session.delete(item)
    db.session.commit();audit(get_jwt_identity(),"resource.retired","resource",resource_id);return {"ok":True}

@api.get("/bookings")
@jwt_required()
def list_bookings(): return {"items":[serialize_booking(item) for item in Booking.query.order_by(desc(Booking.starts_at)).all()]}

@api.post("/bookings")
@jwt_required()
def create_booking():
    data=body();resource=db.get_or_404(Resource,data["resource_id"]);starts=datetime.fromisoformat(data["starts_at"].replace("Z","+00:00"));ends=datetime.fromisoformat(data["ends_at"].replace("Z","+00:00"))
    conflict=Booking.query.filter(Booking.resource_id==resource.id,Booking.status.in_(["confirmed","active"]),Booking.starts_at<ends,Booking.ends_at>starts).first()
    if conflict:return {"error":"This resource is already booked for the selected window","conflict":serialize_booking(conflict)},409
    item=Booking(resource_id=resource.id,requested_by=data.get("requested_by") or get_jwt_identity(),purpose=data.get("purpose") or "",starts_at=starts,ends_at=ends,status=data.get("status") or "confirmed",metadata_json=data.get("metadata") or {})
    db.session.add(item);resource.status="reserved";db.session.commit();audit(get_jwt_identity(),"booking.created","booking",item.id);return serialize_booking(item),201

@api.put("/bookings/<booking_id>")
@jwt_required()
def update_booking(booking_id):
    item=db.get_or_404(Booking,booking_id);data=body()
    if "status" in data:item.status=data["status"]
    if "starts_at" in data:item.starts_at=datetime.fromisoformat(data["starts_at"].replace("Z","+00:00"))
    if "ends_at" in data:item.ends_at=datetime.fromisoformat(data["ends_at"].replace("Z","+00:00"))
    if item.status in {"cancelled","completed"}:
        resource=db.session.get(Resource,item.resource_id)
        if resource: resource.status="available"
    db.session.commit();audit(get_jwt_identity(),"booking.updated","booking",item.id,{"status":item.status});return serialize_booking(item)

@api.get("/credentials")
@jwt_required()
def list_credentials():
    return {"items":[{"id":item.id,"name":item.name,"kind":item.kind,"metadata":item.metadata_json or {},"active":item.active,"created_at":item.created_at.isoformat()} for item in CredentialReference.query.order_by(CredentialReference.name).all()]}

@api.post("/credentials")
@jwt_required()
def create_credential():
    data=body();item=CredentialReference(name=data["name"],kind=data["kind"],metadata_json=data.get("metadata") or {},encrypted_payload=secret_box.encrypt(data.get("secrets") or {}),active=True)
    db.session.add(item);db.session.commit();audit(get_jwt_identity(),"credential.created","credential",item.id,{"kind":item.kind});return {"id":item.id,"name":item.name,"kind":item.kind,"metadata":item.metadata_json,"active":item.active},201

@api.delete("/credentials/<credential_id>")
@jwt_required()
def delete_credential(credential_id):
    item=db.get_or_404(CredentialReference,credential_id);item.active=False;db.session.commit();audit(get_jwt_identity(),"credential.disabled","credential",item.id);return {"ok":True}

@api.get("/audit")
@jwt_required()
def list_audit():
    rows=AuditEvent.query.order_by(desc(AuditEvent.created_at)).limit(500).all()
    return {"items":[{"id":r.id,"actor":r.actor,"action":r.action,"target_type":r.target_type,"target_id":r.target_id,"payload":r.payload_json or {},"created_at":r.created_at.isoformat()} for r in rows]}
