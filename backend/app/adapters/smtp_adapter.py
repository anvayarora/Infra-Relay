from __future__ import annotations
import smtplib
from email.message import EmailMessage
from ..config import config

class SMTPAdapter:
    def send(self, to: str, subject: str, html: str, text: str = "") -> dict:
        message = EmailMessage()
        message["From"] = config.smtp_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text or "Open this message in an HTML-capable email client.")
        message.add_alternative(html, subtype="html")
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=20) as client:
            if config.smtp_tls:
                client.starttls()
            if config.smtp_user:
                client.login(config.smtp_user, config.smtp_password)
            client.send_message(message)
        return {"sent": True, "to": to, "from": config.smtp_from}

smtp_adapter = SMTPAdapter()
