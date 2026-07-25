from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import ansible_runner


class GPUAdapter:
    def __init__(self):
        self.project_dir = Path(os.getenv("AUTODRIVER_AUTOMATION_DIR", "/automation"))

    def run(self, playbook: str, target: dict, extra_vars: dict | None = None) -> dict:
        if not target.get("host") or not target.get("username"):
            raise RuntimeError("GPU automation requires a host and SSH username")

        host_vars: dict[str, Any] = {
            "ansible_host": target["host"],
            "ansible_port": int(target.get("port", 22)),
            "ansible_user": target["username"],
            "ansible_connection": "ssh",
            "ansible_ssh_common_args": (
                "-o StrictHostKeyChecking=yes"
                if target.get("verify_host_key", False)
                else "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
            ),
        }
        if target.get("password"):
            host_vars["ansible_password"] = target["password"]
            host_vars["ansible_become_password"] = target.get("become_password", target["password"])
        if target.get("private_key_file"):
            host_vars["ansible_ssh_private_key_file"] = target["private_key_file"]

        inventory = {"all": {"hosts": {"target": host_vars}}}
        result = ansible_runner.run(
            private_data_dir=str(self.project_dir),
            project_dir=str(self.project_dir),
            playbook=playbook,
            inventory=inventory,
            extravars=extra_vars or {},
            envvars={"ANSIBLE_ROLES_PATH": str(self.project_dir / "roles")},
            quiet=True,
        )

        events: list[dict] = []
        inspection_payload: dict | None = None
        for runner_event in result.events:
            event_name = runner_event.get("event")
            data = runner_event.get("event_data", {})
            task_result = data.get("res", {}) if isinstance(data, dict) else {}
            stats = task_result.get("ansible_stats", {}).get("data", {}) if isinstance(task_result, dict) else {}
            facts = task_result.get("ansible_facts", {}) if isinstance(task_result, dict) else {}
            inspection_payload = (
                stats.get("inspection_payload")
                or facts.get("inspection_payload")
                or inspection_payload
            )
            if event_name in {"runner_on_ok", "runner_on_failed", "runner_on_unreachable"}:
                events.append(
                    {
                        "event": event_name,
                        "task": data.get("task"),
                        "host": data.get("host"),
                        "result": task_result,
                    }
                )

        if result.rc != 0:
            last_failure = next(
                (item for item in reversed(events) if item["event"] in {"runner_on_failed", "runner_on_unreachable"}),
                None,
            )
            detail = last_failure["result"].get("msg") if last_failure else None
            raise RuntimeError(f"AutoDriver playbook failed with rc={result.rc}: {detail or 'see job events'}")

        payload = {
            "status": result.status,
            "rc": result.rc,
            "events": events[-80:],
        }
        if inspection_payload:
            payload["inspection"] = inspection_payload
        return payload


gpu_adapter = GPUAdapter()
