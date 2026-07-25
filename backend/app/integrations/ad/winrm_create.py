import json
import os
import re
from typing import Any, Dict, Optional

import winrm


class ADCreateError(Exception):
    pass


# Backward-compatible name expected by app.py
WinRMCreateError = ADCreateError

def _normalize_upn_suffix_for_create(value):
    raw = str(value or "").strip().strip("@").strip()
    if not raw:
        return "infrarelay.io"
    if "." in raw:
        return raw
    return f"{raw}.infrarelay.io"


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _q(value: Any) -> str:
    if value is None:
        value = ""
    return str(value).replace("'", "''").replace("\r", " ").replace("\n", " ")


def _endpoint(host: str, port: int, use_ssl: bool) -> str:
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}/wsman"


def _safe_sam(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ADCreateError("SamAccountName is required.")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value):
        raise ADCreateError("SamAccountName contains unsupported characters.")
    return value


def _tenant_name(user: Dict[str, Any]) -> str:
    value = (
        user.get("tenant_name")
        or user.get("tenantName")
        or user.get("TenantName")
        or user.get("tenant")
        or user.get("tenant_id")
        or user.get("tenantId")
        or user.get("subdomain")
        or user.get("subDomain")
        or user.get("SubDomain")
        or ""
    )
    value = str(value).strip()

    if not value:
        raise ADCreateError("Tenant Name is required because Tenant Name maps directly to the target AD OU.")

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,62}[A-Za-z0-9]?", value):
        raise ADCreateError("Tenant Name can only contain letters, numbers, spaces, dots, underscores, and hyphens.")

    if "," in value or "=" in value or "\\" in value or "/" in value:
        raise ADCreateError("Tenant Name must be an OU name only, not a DN/path.")

    return value


def _display_name(user: Dict[str, Any], sam: str) -> str:
    display = (
        user.get("display_name")
        or user.get("displayName")
        or user.get("DisplayName")
        or ""
    )
    display = str(display).strip()
    if display:
        return display

    first = str(user.get("first_name") or user.get("givenName") or user.get("FirstName") or "").strip()
    last = str(user.get("last_name") or user.get("surname") or user.get("LastName") or "").strip()
    return f"{first} {last}".strip() or sam


def _session(host, port, use_ssl, transport, server_cert_validation, username, password):
    kwargs = {
        "auth": (username, password),
        "transport": transport or "ntlm",
        "operation_timeout_sec": 120,
        "read_timeout_sec": 150,
    }
    if use_ssl:
        kwargs["server_cert_validation"] = server_cert_validation or "ignore"
    return winrm.Session(_endpoint(host, port, use_ssl), **kwargs)


def test_winrm_connection(
    host: str,
    port: int = 5985,
    use_ssl: bool = False,
    transport: str = "ntlm",
    server_cert_validation: str = "ignore",
    username: str = "",
    password: str = "",
    **kwargs,
) -> Dict[str, Any]:
    ws = _session(host, int(port), bool(use_ssl), transport, server_cert_validation, username, password)

    ps = "\n".join([
        "$ErrorActionPreference='Stop'",
        "$ProgressPreference='SilentlyContinue'",
        "Import-Module ActiveDirectory",
        f"$s='{_q(host)}'",
        "$d=Get-ADDomain -Server $s",
        "[pscustomobject]@{success=$true;computer_name=$env:COMPUTERNAME;domain_dns_root=$d.DNSRoot;domain_dn=$d.DistinguishedName}|ConvertTo-Json -Compress",
    ])

    r = ws.run_ps(ps)
    out = r.std_out.decode("utf-8", errors="replace").strip()
    err = r.std_err.decode("utf-8", errors="replace").strip()

    if r.status_code != 0:
        return {"success": False, "status_code": r.status_code, "error": err or out}

    try:
        data = json.loads(out) if out else {}
    except Exception:
        data = {"raw": out}

    data["success"] = True
    data["status_code"] = r.status_code
    return data


def create_ad_user_via_winrm(
    host: str,
    port: int = 5985,
    use_ssl: bool = False,
    transport: str = "ntlm",
    server_cert_validation: str = "ignore",
    username: str = "",
    password: str = "",
    user: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    if not _bool_env("AD_CREATE_ENABLED", True):
        raise ADCreateError("AD create is disabled.")

    user = user or {}

    sam = _safe_sam(user.get("sam_account_name") or user.get("samAccountName") or user.get("SamAccountName"))
    tenant = _tenant_name(user)

    upn_suffix = os.environ.get("AD_UPN_SUFFIX", "infrarelay.io").strip()
    raw_upn_suffix = (
        user.get("upn_suffix")
        if user.get("upn_suffix") is not None
        else user.get("upnSuffix")
        if user.get("upnSuffix") is not None
        else user.get("SubDomain")
        if user.get("SubDomain") is not None
        else user.get("sub_domain")
        if user.get("sub_domain") is not None
        else user.get("subDomain")
        if user.get("subDomain") is not None
        else kwargs.get("upn_suffix")
        if kwargs.get("upn_suffix") is not None
        else os.environ.get("AD_UPN_SUFFIX", "infrarelay.io")
    )
    upn_suffix = _normalize_upn_suffix_for_create(raw_upn_suffix)
    upn = f"{sam}@{upn_suffix}"
    default_group = str(
        user.get("default_group")
        or user.get("DefaultGroup")
        or kwargs.get("default_group")
        or os.environ.get("AD_DEFAULT_GROUP", "")
    ).strip()

    display = _display_name(user, sam)
    first = str(user.get("first_name") or user.get("givenName") or user.get("FirstName") or "").strip()
    last = str(user.get("last_name") or user.get("surname") or user.get("LastName") or "").strip()
    email = str(user.get("email") or user.get("EmailAddress") or f"{sam}@{upn_suffix}").strip()
    emp = str(user.get("employee_id") or user.get("employeeId") or user.get("EmployeeID") or "").strip()
    desc = str(user.get("description") or user.get("Description") or "").strip()

    temp_pw = str(
        user.get("temporary_password")
        or user.get("temporaryPassword")
        or user.get("newPassword")
        or user.get("password")
        or user.get("Password")
        or user.get("initial_password")
        or user.get("initialPassword")
        or ""
    )

    # MSS policy: newly created AD users must be enabled automatically.
    # Do not allow an older frontend route/payload to create disabled users.
    enabled = True

    if enabled and not temp_pw:
        raise ADCreateError("Enabled AD users require a password from the frontend.")

    create_ou = _bool_env("AD_CREATE_TENANT_OU_IF_MISSING", True)
    parent_dn = os.environ.get("AD_TENANT_OU_PARENT_DN", "").strip()

    print(
        f"[AD-CREATE] request sam={sam} tenant_ou_name={tenant} enabled={enabled} password_supplied={bool(temp_pw)}",
        flush=True,
    )

    ws = _session(host, int(port), bool(use_ssl), transport, server_cert_validation, username, password)

    lines = [
        "$ErrorActionPreference='Stop'",
        "$ProgressPreference='SilentlyContinue'",
        "Import-Module ActiveDirectory",
        f"$s='{_q(host)}'",
        f"$sam='{_q(sam)}'",
        f"$tn='{_q(tenant)}'",
        f"$upn='{_q(upn)}'",
        f"$dn='{_q(display)}'",
        f"$gn='{_q(first)}'",
        f"$sn='{_q(last)}'",
        f"$mail='{_q(email)}'",
        f"$emp='{_q(emp)}'",
        f"$desc='{_q(desc)}'",
        f"$pwd='{_q(temp_pw)}'",
        f"$en=${str(enabled).lower()}",
        f"$mk=${str(create_ou).lower()}",
        f"$par='{_q(parent_dn)}'",
        "$d=Get-ADDomain -Server $s",
        "$base=$d.DistinguishedName",
        "if($par){$base=$par;Get-ADObject -Identity $base -Server $s|Out-Null}",
        "$e=Get-ADUser -Filter \"SamAccountName -eq '$sam'\" -Server $s -Properties DisplayName,EmailAddress,UserPrincipalName,Enabled,WhenCreated -ErrorAction SilentlyContinue",
        "if($e){[pscustomobject]@{success=$true;operation='already_exists_no_update';sam_account_name=$e.SamAccountName;distinguished_name=$e.DistinguishedName;user_principal_name=$e.UserPrincipalName;enabled=$e.Enabled;tenant_ou_name=$tn;message='User already exists. No update, move, delete, or overwrite was performed.'}|ConvertTo-Json -Compress;exit 0}",
        "$ous=@(Get-ADOrganizationalUnit -Filter \"Name -eq '$tn'\" -Server $s -Properties DistinguishedName)",
        "$new=$false",
        "if($ous.Count -gt 0){$ou=$ous|Sort-Object {$_.DistinguishedName.Length},DistinguishedName|Select-Object -First 1}else{if(-not $mk){throw \"Tenant OU '$tn' does not exist\"};New-ADOrganizationalUnit -Name $tn -Path $base -Server $s -ProtectedFromAccidentalDeletion $true;$ou=Get-ADOrganizationalUnit -Filter \"Name -eq '$tn'\" -SearchBase $base -Server $s -Properties DistinguishedName|Sort-Object {$_.DistinguishedName.Length},DistinguishedName|Select-Object -First 1;$new=$true}",
        "if(-not $ou){throw \"Target OU '$tn' not found and could not be created\"}",
        "$np=@{Name=$dn;DisplayName=$dn;SamAccountName=$sam;UserPrincipalName=$upn;Path=$ou.DistinguishedName;Enabled=$en;Server=$s}",
        "if($gn){$np.GivenName=$gn}",
        "if($sn){$np.Surname=$sn}",
        "if($mail){$np.EmailAddress=$mail}",
        "if($emp){$np.EmployeeID=$emp}",
        "if($desc){$np.Description=$desc}",
        "if($pwd){$np.AccountPassword=(ConvertTo-SecureString $pwd -AsPlainText -Force)}",
        "New-ADUser @np",
        "$c=Get-ADUser -Identity $sam -Server $s -Properties DisplayName,EmailAddress,UserPrincipalName,Enabled,WhenCreated,EmployeeID",
    ]

    ps = "\n".join(lines)

    r = ws.run_ps(ps)
    out = r.std_out.decode("utf-8", errors="replace").strip()
    err = r.std_err.decode("utf-8", errors="replace").strip()

    print(f"[AD-CREATE] status_code={r.status_code}", flush=True)
    if out:
        print(f"[AD-CREATE] stdout={out[:2000]}", flush=True)
    if err:
        print(f"[AD-CREATE] stderr={err[:2000]}", flush=True)

    if r.status_code != 0:
        return {
            "success": False,
            "status_code": r.status_code,
            "error": err or out or "AD create failed.",
            "sam_account_name": sam,
            "tenant_ou_name": tenant,
        }

    try:
        return json.loads(out) if out else {"success": True, "sam_account_name": sam}
    except Exception:
        return {"success": True, "raw": out, "sam_account_name": sam, "tenant_ou_name": tenant}

# =========================
# FINAL_DEFAULT_GROUP_SECOND_WINRM_V2
# Do NOT add group membership inside the huge New-ADUser script.
# Instead, create user first, then run a tiny second WinRM command:
#   Get-ADUser -> Get-ADGroup -> Add-ADGroupMember
# This avoids "The command line is too long."
# =========================

import json as _group_json
import winrm as _group_winrm


_base_create_ad_user_via_winrm_before_group_v2 = create_ad_user_via_winrm


def _group_winrm_session_v2(host, port, use_ssl, transport, server_cert_validation, username, password):
    scheme = "https" if use_ssl else "http"
    endpoint = f"{scheme}://{host}:{port}/wsman"

    return _group_winrm.Session(
        endpoint,
        auth=(username, password),
        transport=transport or "ntlm",
        server_cert_validation=server_cert_validation or "ignore",
        operation_timeout_sec=60,
        read_timeout_sec=90,
    )


def _add_user_to_default_group_second_winrm_v2(
    host,
    port,
    use_ssl,
    transport,
    server_cert_validation,
    username,
    password,
    sam,
    default_group,
):
    if not default_group:
        return {
            "success": True,
            "default_group": "",
            "default_group_added": False,
            "skipped": True,
        }

    ws = _group_winrm_session_v2(
        host,
        port,
        use_ssl,
        transport,
        server_cert_validation,
        username,
        password,
    )

    ps = "\n".join(
        [
            "$ErrorActionPreference='Stop'",
            "Import-Module ActiveDirectory",
            f"$s='{_q(host)}'",
            f"$sam='{_q(sam)}'",
            f"$grp='{_q(default_group)}'",
            "$u=Get-ADUser -Identity $sam -Server $s -ErrorAction Stop",
            "$g=Get-ADGroup -Identity $grp -Server $s -Properties GroupCategory -ErrorAction Stop",
            "if($g.GroupCategory -ne 'Security'){throw \"Default group is not a Security group: $grp\"}",
            "Add-ADGroupMember -Identity $g.DistinguishedName -Members $u.DistinguishedName -Server $s -ErrorAction Stop",
            "@{success=$true;default_group=$grp;default_group_added=$true;group_dn=$g.DistinguishedName;member_dn=$u.DistinguishedName} | ConvertTo-Json -Compress",
        ]
    )

    print(f"[AD-GROUP] request sam={sam} group={default_group}", flush=True)
    r = ws.run_ps(ps)

    stdout = r.std_out.decode("utf-8", errors="replace").strip()
    stderr = r.std_err.decode("utf-8", errors="replace").strip()

    print(f"[AD-GROUP] status_code={r.status_code}", flush=True)
    if stdout:
        print(f"[AD-GROUP] stdout={stdout}", flush=True)
    if stderr:
        print(f"[AD-GROUP] stderr={stderr}", flush=True)

    if r.status_code != 0:
        return {
            "success": False,
            "default_group": default_group,
            "default_group_added": False,
            "error": stderr or stdout or "Add-ADGroupMember failed",
            "status_code": r.status_code,
        }

    try:
        return _group_json.loads(stdout)
    except Exception:
        return {
            "success": True,
            "default_group": default_group,
            "default_group_added": True,
            "raw": stdout,
        }


def create_ad_user_via_winrm(
    host,
    port,
    use_ssl,
    transport,
    server_cert_validation,
    username,
    password,
    user,
    **kwargs,
):
    default_group = str(
        user.get("default_group")
        or user.get("DefaultGroup")
        or kwargs.get("default_group")
        or ""
    ).strip()

    # Do not pass default_group into the main create script.
    clean_user = dict(user)
    clean_user.pop("default_group", None)
    clean_user.pop("DefaultGroup", None)

    clean_kwargs = dict(kwargs)
    clean_kwargs.pop("default_group", None)

    result = _base_create_ad_user_via_winrm_before_group_v2(
        host=host,
        port=port,
        use_ssl=use_ssl,
        transport=transport,
        server_cert_validation=server_cert_validation,
        username=username,
        password=password,
        user=clean_user,
        **clean_kwargs,
    )

    result["default_group"] = default_group
    result["default_group_added"] = False

    # Existing users are intentionally not modified.
    if result.get("operation") == "already_exists_no_update":
        result["default_group_skip_reason"] = "existing_user_no_update"
        return result

    if not result.get("success"):
        return result

    if not default_group:
        result["default_group_skip_reason"] = "no_default_group_for_target"
        return result

    group_result = _add_user_to_default_group_second_winrm_v2(
        host=host,
        port=port,
        use_ssl=use_ssl,
        transport=transport,
        server_cert_validation=server_cert_validation,
        username=username,
        password=password,
        sam=result.get("sam_account_name") or clean_user.get("sam_account_name") or clean_user.get("SamAccountName"),
        default_group=default_group,
    )

    result["default_group_result"] = group_result
    result["default_group_added"] = bool(group_result.get("default_group_added"))

    if not group_result.get("success"):
        result["success"] = False
        result["created_user_but_group_failed"] = True
        result["error"] = group_result.get("error") or "User created but default group add failed."

    return result

