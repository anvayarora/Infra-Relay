from __future__ import annotations
from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.utils.conv import escape_filter_chars

class LDAPAdapter:
    def _connection(self, settings: dict, secrets: dict) -> Connection:
        server = Server(settings["host"], port=int(settings.get("port", 636 if settings.get("use_ssl", True) else 389)), use_ssl=bool(settings.get("use_ssl", True)), get_info=ALL)
        return Connection(server, user=secrets["username"], password=secrets["password"], auto_bind=True)

    def search_user(self, settings: dict, secrets: dict, query: str) -> list[dict]:
        conn = self._connection(settings, secrets)
        safe = escape_filter_chars(query)
        search_filter = f"(|(sAMAccountName=*{safe}*)(displayName=*{safe}*)(mail=*{safe}*))"
        conn.search(settings["base_dn"], search_filter, search_scope=SUBTREE, attributes=["sAMAccountName", "displayName", "mail", "userPrincipalName", "distinguishedName", "memberOf"])
        return [{
            "sam_account_name": str(entry.sAMAccountName or ""),
            "display_name": str(entry.displayName or ""),
            "mail": str(entry.mail or ""),
            "user_principal_name": str(entry.userPrincipalName or ""),
            "distinguished_name": str(entry.entry_dn),
            "groups": list(entry.memberOf.values) if hasattr(entry, "memberOf") else [],
        } for entry in conn.entries]

    def create_user(self, settings: dict, secrets: dict, values: dict) -> dict:
        conn = self._connection(settings, secrets)
        cn = values.get("display_name") or values["username"]
        target_ou = values.get("target_ou") or settings["default_ou"]
        dn = f"CN={cn},{target_ou}"
        upn_suffix = values.get("upn_suffix") or settings.get("upn_suffix", "")
        attributes = {
            "sAMAccountName": values["username"],
            "displayName": cn,
            "givenName": values.get("first_name", ""),
            "sn": values.get("last_name", ""),
            "mail": values.get("email", ""),
            "userPrincipalName": values.get("upn") or f"{values['username']}@{upn_suffix}",
            "userAccountControl": 514,
        }
        ok = conn.add(dn, ["top", "person", "organizationalPerson", "user"], attributes)
        if not ok:
            raise RuntimeError(conn.result.get("message") or "AD user creation failed")
        return {"created": True, "distinguished_name": dn, "username": values["username"], "enabled": False}

ldap_adapter = LDAPAdapter()
