from __future__ import annotations
import json
import winrm

class WinRMAdapter:
    def run(self, host: str, username: str, password: str, script: str, transport: str = "ntlm", use_ssl: bool = False, verify_ssl: bool = False) -> dict:
        scheme = "https" if use_ssl else "http"
        port = 5986 if use_ssl else 5985
        endpoint = f"{scheme}://{host}:{port}/wsman"
        session = winrm.Session(endpoint, auth=(username, password), transport=transport, server_cert_validation="validate" if verify_ssl else "ignore")
        result = session.run_ps(script)
        stdout = result.std_out.decode(errors="replace")
        stderr = result.std_err.decode(errors="replace")
        parsed = None
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            pass
        return {"status_code": result.status_code, "stdout": stdout, "stderr": stderr, "json": parsed}

winrm_adapter = WinRMAdapter()
