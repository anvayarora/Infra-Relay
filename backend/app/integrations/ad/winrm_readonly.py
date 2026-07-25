"""Read-only WinRM helpers for AD connectivity checks.

This module intentionally exposes only read operations. It never creates,
updates, disables, enables, deletes, or adds group membership.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import winrm


class WinRMReadOnlyError(Exception):
    """Raised when WinRM connection or read-only command execution fails."""


def _clean_host(host: str) -> str:
    host = (host or "").strip()
    if not host:
        raise WinRMReadOnlyError("AD host/IP is required.")
    return host.replace("http://", "").replace("https://", "").split("/")[0]


def build_endpoint(host: str, port: Optional[int] = None, use_ssl: bool = False) -> str:
    host = _clean_host(host)
    if ":" in host and host.count(":") == 1:
        host_part, port_part = host.split(":", 1)
        host = host_part
        if port is None:
            port = int(port_part)
    if port is None:
        port = 5986 if use_ssl else 5985
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{int(port)}/wsman"


def _make_session(
    host: str,
    username: str,
    password: str,
    *,
    port: Optional[int] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
    server_cert_validation: str = "ignore",
) -> winrm.Session:
    if not username or not password:
        raise WinRMReadOnlyError("AD username and password are required.")

    endpoint = build_endpoint(host, port=port, use_ssl=use_ssl)
    kwargs = {
        "auth": (username, password),
        "transport": transport or "ntlm",
    }
    if use_ssl:
        kwargs["server_cert_validation"] = server_cert_validation or "ignore"

    return winrm.Session(endpoint, **kwargs)


def _decode(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _loads_powershell_json(stdout: str) -> Any:
    text = (stdout or "").strip()
    if not text:
        return None

    # WinRM sometimes includes preamble/warnings. Try to isolate JSON.
    first_obj = text.find("{")
    first_arr = text.find("[")
    positions = [p for p in (first_obj, first_arr) if p >= 0]
    if positions:
        text = text[min(positions):]

    return json.loads(text)


def run_readonly_ps(
    script: str,
    *,
    host: str,
    username: str,
    password: str,
    port: Optional[int] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
    server_cert_validation: str = "ignore",
) -> Dict[str, Any]:
    session = _make_session(
        host,
        username,
        password,
        port=port,
        use_ssl=use_ssl,
        transport=transport,
        server_cert_validation=server_cert_validation,
    )
    result = session.run_ps(script)
    stdout = _decode(result.std_out)
    stderr = _decode(result.std_err)
    return {
        "status_code": result.status_code,
        "stdout": stdout,
        "stderr": stderr,
        "ok": result.status_code == 0,
    }


def test_winrm_connection(
    *,
    host: str,
    username: str,
    password: str,
    port: Optional[int] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
    server_cert_validation: str = "ignore",
) -> Dict[str, Any]:
    """Test WinRM by executing read-only inspection commands."""
    endpoint = build_endpoint(host, port=port, use_ssl=use_ssl)
    script = r'''
$ErrorActionPreference = "Stop"
$result = [PSCustomObject]@{
    computer_name = $env:COMPUTERNAME
    whoami = (whoami)
    powershell_version = $PSVersionTable.PSVersion.ToString()
    active_directory_module_available = [bool](Get-Module -ListAvailable -Name ActiveDirectory)
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
}
$result | ConvertTo-Json -Depth 4
'''
    result = run_readonly_ps(
        script,
        host=host,
        username=username,
        password=password,
        port=port,
        use_ssl=use_ssl,
        transport=transport,
        server_cert_validation=server_cert_validation,
    )
    parsed = None
    if result["ok"]:
        parsed = _loads_powershell_json(result["stdout"])
    return {
        "success": result["ok"],
        "endpoint": endpoint,
        "status_code": result["status_code"],
        "connection": parsed,
        "stderr": result["stderr"],
    }


def fetch_ad_users_readonly(
    *,
    host: str,
    username: str,
    password: str,
    port: Optional[int] = None,
    use_ssl: bool = False,
    transport: str = "ntlm",
    server_cert_validation: str = "ignore",
    limit: int = 25,
) -> Dict[str, Any]:
    """Fetch a limited list of AD users using Get-ADUser only."""
    try:
        limit = int(limit)
    except Exception:
        limit = 25
    limit = max(1, min(limit, 200))

    script = f'''
$ErrorActionPreference = "Stop"
Import-Module ActiveDirectory -ErrorAction Stop
$users = Get-ADUser -Filter * -ResultSetSize {limit} -Properties DisplayName,EmailAddress,UserPrincipalName,Enabled,WhenCreated |
    Select-Object @{{Name="sam_account_name";Expression={{$_.SamAccountName}}}},
                  @{{Name="name";Expression={{$_.Name}}}},
                  @{{Name="display_name";Expression={{$_.DisplayName}}}},
                  @{{Name="user_principal_name";Expression={{$_.UserPrincipalName}}}},
                  @{{Name="email";Expression={{$_.EmailAddress}}}},
                  @{{Name="enabled";Expression={{$_.Enabled}}}},
                  @{{Name="distinguished_name";Expression={{$_.DistinguishedName}}}},
                  @{{Name="when_created";Expression={{$_.WhenCreated.ToUniversalTime().ToString("o")}}}}
@($users) | ConvertTo-Json -Depth 6
'''
    result = run_readonly_ps(
        script,
        host=host,
        username=username,
        password=password,
        port=port,
        use_ssl=use_ssl,
        transport=transport,
        server_cert_validation=server_cert_validation,
    )

    users: List[Dict[str, Any]] = []
    if result["ok"]:
        parsed = _loads_powershell_json(result["stdout"])
        if parsed is None:
            users = []
        elif isinstance(parsed, list):
            users = parsed
        else:
            users = [parsed]

    return {
        "success": result["ok"],
        "status_code": result["status_code"],
        "limit": limit,
        "count": len(users),
        "users": users,
        "stderr": result["stderr"],
    }
