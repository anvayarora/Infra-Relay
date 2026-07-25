from __future__ import annotations
import json
import re
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
from flask import current_app
from .adapters.gpu_adapter import gpu_adapter
from .adapters.ldap_adapter import ldap_adapter
from .adapters.smtp_adapter import smtp_adapter
from .adapters.winrm_adapter import winrm_adapter
from .blocks import BLOCKS
from .config import config
from .extensions import db
from .models import Booking, BlockExecution, CredentialReference, Execution, ExecutionEvent, Resource, UITransaction, Workflow, utcnow
from .security import secret_box

TOKEN_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")

def _lookup(path: str, context: dict) -> Any:
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current

def resolve(value: Any, context: dict) -> Any:
    if isinstance(value, dict):
        return {key: resolve(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, context) for item in value]
    if not isinstance(value, str):
        return value
    match = TOKEN_RE.fullmatch(value)
    if match:
        found = _lookup(match.group(1), context)
        return found if found is not None else value
    return TOKEN_RE.sub(lambda m: str(_lookup(m.group(1), context) or ""), value)

def event(execution: Execution, event_type: str, payload: dict):
    db.session.add(ExecutionEvent(execution_id=execution.id, sandbox_id=execution.sandbox_id, event_type=event_type, payload_json=payload))
    db.session.commit()

def _credential(reference_id: str) -> tuple[dict, dict]:
    ref = db.session.get(CredentialReference, reference_id)
    if not ref or not ref.active:
        raise RuntimeError("Credential reference is missing or inactive")
    return ref.metadata_json or {}, secret_box.decrypt(ref.encrypted_payload)

def _resource(resource_id: str) -> Resource:
    resource = db.session.get(Resource, resource_id)
    if not resource:
        raise RuntimeError(f"Resource {resource_id} was not found")
    return resource

def _create_transaction(execution: Execution, node: dict, settings: dict, direction: str, payload: dict, allowed_actions: list[str]) -> UITransaction:
    tx = UITransaction(
        execution_id=execution.id,
        sandbox_id=execution.sandbox_id,
        workflow_id=execution.workflow_id,
        block_id=node["id"],
        direction=direction,
        intent=settings.get("intent") or node["type"],
        schema_json=settings.get("schema") or {},
        payload_json=payload,
        allowed_actions_json=allowed_actions,
        token=secrets.token_urlsafe(32),
        expires_at=utcnow() + timedelta(minutes=int(settings.get("timeout_minutes") or 1440)),
    )
    db.session.add(tx)
    db.session.commit()
    event(execution, "ui.transaction.opened", {"transaction_id": tx.id, "block_id": node["id"], "direction": direction, "intent": tx.intent, "schema": tx.schema_json, "payload": payload})
    return tx

def _notify_approval(tx: UITransaction, settings: dict):
    if not settings.get("notify") or not settings.get("approver_email"):
        return
    url = f"{config.public_url}/transactions/{tx.id}/public?token={tx.token}"
    html = f"<div style='font-family:Inter,Arial,sans-serif;max-width:600px;margin:auto'><h2>{settings.get('title','Approval required')}</h2><p>{settings.get('message','Review this action.')}</p><p><a href='{url}' style='background:#111;color:white;padding:12px 18px;border-radius:8px;text-decoration:none'>Open transaction</a></p></div>"
    smtp_adapter.send(settings["approver_email"], settings.get("title", "Approval required"), html)

def _run_block(execution: Execution, node: dict, settings: dict, context: dict) -> tuple[str, dict, str]:
    block_type = node["type"]
    block_id = node["id"]
    response = (context.get("responses") or {}).get(block_id)
    if block_type == "trigger.manual":
        return "completed", context.get("input", {}), "main"
    if block_type in {"ui.payload.inbound", "ui.payload.bidirectional", "hitl.approval"}:
        if response:
            action = response.get("action") or "main"
            values = response.get("values") or response
            if block_type == "hitl.approval":
                return "completed", {"action": action, "approved": action == "approve", "values": values}, "approved" if action == "approve" else "rejected"
            return "completed", {"action": action, **(values if isinstance(values, dict) else {"value": values})}, action
        existing = UITransaction.query.filter_by(execution_id=execution.id, block_id=block_id, status="open").first()
        if existing:
            return "waiting", {"transaction_id": existing.id}, "main"
        direction = "inbound" if block_type == "ui.payload.inbound" else "bidirectional"
        allowed = settings.get("allowed_actions") or (["approve", "reject"] if block_type == "hitl.approval" else ["submit"])
        payload = {"title": settings.get("title"), "message": settings.get("message"), "context": context.get("nodes", {}), "input": context.get("input", {})}
        tx = _create_transaction(execution, node, settings, direction, payload, allowed)
        if block_type == "hitl.approval":
            _notify_approval(tx, settings)
        return "waiting", {"transaction_id": tx.id}, "main"
    if block_type == "ui.payload.outbound":
        payload = {"title": settings.get("title"), "data": settings.get("payload") or context.get("last", {})}
        tx = UITransaction(execution_id=execution.id, sandbox_id=execution.sandbox_id, workflow_id=execution.workflow_id, block_id=block_id, direction="outbound", status="emitted", intent=settings.get("intent", "workflow_result"), schema_json=settings.get("schema") or {}, payload_json=payload, response_json={}, allowed_actions_json=[], token=secrets.token_urlsafe(32))
        db.session.add(tx)
        db.session.commit()
        event(execution, "ui.payload.emitted", {"transaction_id": tx.id, "block_id": block_id, "intent": tx.intent, "payload": payload})
        return "completed", {"transaction_id": tx.id, **payload}, "main"
    if block_type == "data.set":
        return "completed", settings.get("values") or {}, "main"
    if block_type == "control.condition":
        value = settings.get("value")
        compare = settings.get("compare_to")
        operator = settings.get("operator", "equals")
        result = value == compare if operator == "equals" else value != compare if operator == "not_equals" else bool(value) if operator == "truthy" else str(compare) in str(value)
        return "completed", {"result": result, "value": value, "compare_to": compare}, "true" if result else "false"
    if block_type == "resource.search":
        query = Resource.query
        if settings.get("resource_type"):
            query = query.filter_by(resource_type=settings["resource_type"])
        if settings.get("status"):
            query = query.filter_by(status=settings["status"])
        resources = query.all()
        tags = set(settings.get("tags") or [])
        resources = [r for r in resources if not tags or tags.issubset(set(r.tags_json or []))]
        return "completed", {"resources": [serialize_resource(r) for r in resources], "count": len(resources)}, "main"
    if block_type == "resource.book":
        resource = _resource(str(settings["resource_id"]))
        starts = datetime.fromisoformat(str(settings["starts_at"]).replace("Z", "+00:00"))
        ends = datetime.fromisoformat(str(settings["ends_at"]).replace("Z", "+00:00"))
        conflict = Booking.query.filter(Booking.resource_id == resource.id, Booking.status.in_(["confirmed", "active"]), Booking.starts_at < ends, Booking.ends_at > starts).first()
        if conflict:
            raise RuntimeError(f"Resource is already booked by {conflict.requested_by}")
        booking = Booking(resource_id=resource.id, requested_by=str(settings.get("requested_by") or "workflow"), purpose=str(settings.get("purpose") or ""), starts_at=starts, ends_at=ends, status="confirmed")
        db.session.add(booking)
        resource.status = "reserved"
        db.session.commit()
        return "completed", serialize_booking(booking), "main"
    if block_type == "gpu.inspect":
        resource = _resource(str(settings["resource_id"]))
        if not settings.get("execute"):
            return "completed", {"mode": "plan", "resource": serialize_resource(resource), "operation": "inspect_gpu_stack", "playbook": "playbooks/inspect.yml"}, "main"
        metadata, secret = _credential(resource.connection_ref or "")
        result = gpu_adapter.run("playbooks/inspect.yml", {**metadata, **secret, "host": metadata.get("host") or resource.capabilities_json.get("host")})
        resource.maintenance_json = {**(resource.maintenance_json or {}), "last_inspection": result, "last_inspected_at": utcnow().isoformat()}
        db.session.commit()
        return "completed", result, "main"
    if block_type == "gpu.provision":
        resource = _resource(str(settings["resource_id"]))
        plan = {"driver": settings.get("driver"), "cuda": settings.get("cuda"), "container_toolkit": settings.get("container_toolkit"), "resolve_nouveau": settings.get("resolve_nouveau"), "enable_iommu": settings.get("enable_iommu"), "allow_reboot": settings.get("allow_reboot")}
        if not settings.get("execute"):
            return "completed", {"mode": "plan", "resource": serialize_resource(resource), "plan": plan, "playbook": "playbooks/component_update.yml"}, "main"
        metadata, secret = _credential(resource.connection_ref or "")
        result = gpu_adapter.run("playbooks/component_update.yml", {**metadata, **secret, "host": metadata.get("host") or resource.capabilities_json.get("host")}, plan)
        resource.maintenance_json = {**(resource.maintenance_json or {}), "last_provisioning": result, "desired_state": plan, "last_updated_at": utcnow().isoformat()}
        db.session.commit()
        return "completed", result, "main"
    if block_type == "ad.search_user":
        metadata, secret = _credential(str(settings["credential_ref"]))
        users = ldap_adapter.search_user(metadata, secret, str(settings.get("query") or ""))
        return "completed", {"users": users, "count": len(users)}, "main"
    if block_type == "ad.create_user":
        values = {key: settings.get(key) for key in ["username", "display_name", "email", "target_ou"]}
        if not settings.get("execute"):
            return "completed", {"mode": "plan", "operation": "create_disabled_ad_user", "values": values}, "main"
        metadata, secret = _credential(str(settings["credential_ref"]))
        return "completed", ldap_adapter.create_user(metadata, secret, values), "main"
    if block_type == "powershell.winrm":
        if not settings.get("execute"):
            return "completed", {"mode": "plan", "host": settings.get("host"), "script": settings.get("script")}, "main"
        metadata, secret = _credential(str(settings["credential_ref"]))
        result = winrm_adapter.run(str(settings.get("host") or metadata.get("host")), secret["username"], secret["password"], str(settings["script"]), metadata.get("transport", "ntlm"), bool(metadata.get("use_ssl", False)), bool(metadata.get("verify_ssl", False)))
        if result["status_code"] != 0:
            raise RuntimeError(result["stderr"] or "PowerShell command failed")
        return "completed", result, "main"
    if block_type == "smtp.send":
        if not settings.get("execute"):
            return "completed", {"mode": "plan", "to": settings.get("to"), "subject": settings.get("subject")}, "main"
        return "completed", smtp_adapter.send(str(settings["to"]), str(settings["subject"]), str(settings["html"])), "main"
    if block_type == "http.request":
        if not settings.get("execute"):
            return "completed", {"mode": "plan", "method": settings.get("method"), "url": settings.get("url"), "body": settings.get("body")}, "main"
        response = requests.request(str(settings.get("method", "GET")), str(settings["url"]), headers=settings.get("headers") or {}, json=settings.get("body"), timeout=30)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {body}")
        return "completed", {"status_code": response.status_code, "body": body, "headers": dict(response.headers)}, "main"
    raise RuntimeError(f"Unsupported block type: {block_type}")

def _graph(workflow: Workflow):
    graph = workflow.graph_json or {}
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    outgoing: dict[str, list[dict]] = {node_id: [] for node_id in nodes}
    incoming_count = {node_id: 0 for node_id in nodes}
    for edge in graph.get("edges", []):
        if edge.get("source") in nodes and edge.get("target") in nodes:
            outgoing[edge["source"]].append(edge)
            incoming_count[edge["target"]] += 1
    roots = [node_id for node_id, count in incoming_count.items() if count == 0]
    return nodes, outgoing, roots

def execute(execution_id: str):
    execution = db.session.get(Execution, execution_id)
    if not execution:
        return
    workflow = db.session.get(Workflow, execution.workflow_id)
    nodes, outgoing, roots = _graph(workflow)
    context = execution.context_json or {"input": execution.input_json or {}, "nodes": {}, "responses": {}, "completed": [], "queue": roots}
    context.setdefault("input", execution.input_json or {})
    context.setdefault("nodes", {})
    context.setdefault("responses", {})
    context.setdefault("completed", [])
    context.setdefault("queue", roots)
    if not context["queue"] and not context["completed"]:
        context["queue"] = roots
    execution.status = "running"
    execution.started_at = execution.started_at or utcnow()
    db.session.commit()
    event(execution, "execution.started", {"workflow_id": workflow.id, "sandbox_id": execution.sandbox_id})
    try:
        while context["queue"]:
            node_id = context["queue"][0]
            node = nodes.get(node_id)
            if not node:
                context["queue"].pop(0)
                continue
            block_type = node.get("type")
            if block_type not in BLOCKS:
                raise RuntimeError(f"Unknown block type {block_type}")
            raw_settings = (node.get("data") or {}).get("settings") or {}
            settings = resolve(raw_settings, {**context, "last": context.get("last", {})})
            block_exec = BlockExecution.query.filter_by(execution_id=execution.id, block_id=node_id).order_by(BlockExecution.created_at.desc()).first()
            if not block_exec or block_exec.status not in {"waiting", "running"}:
                block_exec = BlockExecution(execution_id=execution.id, block_id=node_id, block_type=block_type, status="running", input_json=settings, started_at=utcnow())
                db.session.add(block_exec)
                db.session.commit()
            else:
                block_exec.status = "running"
                db.session.commit()
            event(execution, "block.started", {"block_id": node_id, "block_type": block_type})
            status, output, selected_handle = _run_block(execution, node, settings, context)
            block_exec.output_json = output or {}
            if status == "waiting":
                block_exec.status = "waiting"
                execution.status = "waiting"
                execution.context_json = context
                db.session.commit()
                event(execution, "execution.waiting", {"block_id": node_id, **(output or {})})
                return
            block_exec.status = "completed"
            block_exec.completed_at = utcnow()
            context["nodes"][node_id] = output or {}
            context["last"] = output or {}
            context["completed"].append(node_id)
            context["queue"].pop(0)
            candidates = outgoing.get(node_id, [])
            matching = [edge for edge in candidates if not edge.get("sourceHandle") or edge.get("sourceHandle") in {selected_handle, "main"}]
            for edge in matching:
                target = edge["target"]
                if target not in context["completed"] and target not in context["queue"]:
                    context["queue"].append(target)
            execution.context_json = context
            db.session.commit()
            event(execution, "block.completed", {"block_id": node_id, "block_type": block_type, "output": output})
        execution.status = "completed"
        execution.output_json = context.get("last", {})
        execution.completed_at = utcnow()
        execution.context_json = context
        db.session.commit()
        event(execution, "execution.completed", {"output": execution.output_json})
    except Exception as exc:
        execution.status = "failed"
        execution.error = str(exc)
        execution.completed_at = utcnow()
        execution.context_json = context
        db.session.commit()
        event(execution, "execution.failed", {"error": str(exc)})

def serialize_resource(resource: Resource) -> dict:
    return {"id":resource.id,"name":resource.name,"resource_type":resource.resource_type,"status":resource.status,"location":resource.location,"connection_ref":resource.connection_ref,"capabilities":resource.capabilities_json or {},"booking_policy":resource.booking_policy_json or {},"maintenance":resource.maintenance_json or {},"tags":resource.tags_json or [],"created_at":resource.created_at.isoformat(),"updated_at":resource.updated_at.isoformat()}

def serialize_booking(booking: Booking) -> dict:
    return {"id":booking.id,"resource_id":booking.resource_id,"resource_name":booking.resource.name if booking.resource else None,"requested_by":booking.requested_by,"purpose":booking.purpose,"starts_at":booking.starts_at.isoformat(),"ends_at":booking.ends_at.isoformat(),"status":booking.status,"metadata":booking.metadata_json or {},"created_at":booking.created_at.isoformat()}

class Runtime:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=config.execution_workers, thread_name_prefix="workflow")
        self.app = None
        self.lock = threading.Lock()

    def bind(self, app):
        self.app = app

    def submit(self, execution_id: str):
        app = self.app or current_app._get_current_object()
        self.executor.submit(self._run, app, execution_id)

    @staticmethod
    def _run(app, execution_id: str):
        with app.app_context():
            execute(execution_id)

runtime = Runtime()
