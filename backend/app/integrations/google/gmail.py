from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from app.core.config import settings
from app.core.encryption import decrypt_secret, encrypt_secret
from app.models.integration import IntegrationCredential


class GmailService:
    BASE_URL = "https://gmail.googleapis.com/gmail/v1"

    def __init__(self, credential: IntegrationCredential):
        self.credential = credential

    def _access_token(self) -> str:
        now = datetime.now(timezone.utc)

        if (
            self.credential.token_expires_at
            and self.credential.token_expires_at
            > now + timedelta(minutes=2)
        ):
            token = decrypt_secret(
                self.credential.access_token_encrypted
            )
            if token:
                return token

        return self._refresh_access_token()

    def _refresh_access_token(self) -> str:
        now = datetime.now(timezone.utc)
        refresh_token = decrypt_secret(
            self.credential.refresh_token_encrypted
        )

        if not refresh_token:
            raise RuntimeError(
                "Google refresh token not available. "
                "Please reconnect Google."
            )

        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if not response.ok:
            raise RuntimeError(
                "Google OAuth refresh failed: "
                f"status={response.status_code} "
                f"body={response.text}"
            )

        token_data = response.json()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")

        if not access_token:
            raise RuntimeError(
                "Google refresh did not return access token."
            )

        self.credential.access_token_encrypted = encrypt_secret(
            access_token
        )

        if expires_in:
            self.credential.token_expires_at = (
                now + timedelta(seconds=int(expires_in))
            )

        return access_token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
        }

    def profile(self) -> dict[str, Any]:
        response = requests.get(
            f"{self.BASE_URL}/users/me/profile",
            headers=self._headers(),
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    def latest_messages(
        self,
        max_results: int = 10,
    ) -> dict[str, Any]:
        response = requests.get(
            f"{self.BASE_URL}/users/me/messages",
            headers=self._headers(),
            params={
                "maxResults": max_results,
                "labelIds": "INBOX",
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    def message(self, message_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.BASE_URL}/users/me/messages/{message_id}",
            headers=self._headers(),
            params={
                "format": "full",
            },
            timeout=30,
        )

        response.raise_for_status()
        return response.json()
