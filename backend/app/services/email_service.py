from __future__ import annotations

import smtplib
import logging
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, app_settings: Settings | None = None) -> None:
        self.settings = app_settings or settings

    def send_email(self, to_email: str, subject: str, body: str) -> dict[str, str]:
        self._validate_config()
        recipient = to_email.strip()
        if not recipient:
            raise ValueError("SEND_EMAIL action resolved an empty recipient email.")

        message = EmailMessage()
        message["From"] = formataddr((self.settings.SMTP_FROM_NAME, self.settings.SMTP_FROM_EMAIL))
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT, timeout=20) as smtp:
                if self.settings.SMTP_USE_TLS:
                    smtp.starttls()
                if self.settings.SMTP_USERNAME:
                    smtp.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                smtp.send_message(message)
        except smtplib.SMTPException as exc:
            raise RuntimeError(f"SMTP send failed: {exc}") from exc
        except OSError as exc:
            raise RuntimeError(f"SMTP connection failed: {exc}") from exc

        return {"to": recipient, "subject": subject, "status": "sent"}

    def _validate_config(self) -> None:
        logger.debug(
            "SMTP config presence: SMTP_HOST=%s SMTP_FROM_EMAIL=%s",
            bool(self.settings.SMTP_HOST),
            bool(self.settings.SMTP_FROM_EMAIL),
        )
        missing = []
        if not self.settings.SMTP_HOST:
            missing.append("SMTP_HOST")
        if not self.settings.SMTP_PORT:
            missing.append("SMTP_PORT")
        if not self.settings.SMTP_FROM_EMAIL:
            missing.append("SMTP_FROM_EMAIL")
        if self.settings.SMTP_USERNAME and not self.settings.SMTP_PASSWORD:
            missing.append("SMTP_PASSWORD")
        if missing:
            raise ValueError(f"SMTP config missing: {', '.join(missing)}")
