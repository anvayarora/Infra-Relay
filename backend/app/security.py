from __future__ import annotations
import base64
import hashlib
import json
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from cryptography.fernet import Fernet, InvalidToken
from .config import config

class SecretBox:
    def __init__(self):
        key = config.credential_encryption_key.encode() if config.credential_encryption_key else base64.urlsafe_b64encode(hashlib.sha256(config.secret_key.encode()).digest())
        try:
            self.fernet = Fernet(key)
        except ValueError:
            self.fernet = Fernet(base64.urlsafe_b64encode(key.ljust(32, b"0")[:32]))

    def encrypt(self, payload: dict) -> str:
        return self.fernet.encrypt(json.dumps(payload).encode()).decode()

    def decrypt(self, value: str | None) -> dict:
        if not value:
            return {}
        try:
            return json.loads(self.fernet.decrypt(value.encode()).decode())
        except (InvalidToken, ValueError, json.JSONDecodeError):
            return {}

secret_box = SecretBox()

def current_actor(optional: bool = False) -> str:
    verify_jwt_in_request(optional=optional)
    return get_jwt_identity() or "anonymous"
