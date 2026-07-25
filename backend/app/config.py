from __future__ import annotations
import os
from dataclasses import dataclass
@dataclass(frozen=True)
class Config:
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-too")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:////data/infrarelay.db")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:4000")
    smtp_host: str = os.getenv("SMTP_HOST", "10.25.205.16")
    smtp_port: int = int(os.getenv("SMTP_PORT") or "25")
    smtp_from: str = os.getenv("SMTP_FROM", "ps-gcc.infrarelay.studio@your-company.example")
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_tls: bool = os.getenv("SMTP_TLS", "false").lower() == "true"
    public_url: str = os.getenv("PUBLIC_URL", "http://localhost:4000")
    execution_workers: int = int(os.getenv("EXECUTION_WORKERS", "4"))
    credential_encryption_key: str = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    allow_demo_auth: bool = os.getenv("ALLOW_DEMO_AUTH", "true").lower() == "true"
config = Config()
