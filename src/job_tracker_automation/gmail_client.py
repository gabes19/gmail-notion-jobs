from __future__ import annotations

import base64
import json
import tempfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import EmailMessage
from .text_utils import extract_links, html_to_text

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    def __init__(self, oauth_client_json: str, oauth_token_json: str) -> None:
        self.oauth_client_json = oauth_client_json
        self.oauth_token_json = oauth_token_json
        self.service = self._build_service()

    def _build_service(self) -> Any:
        creds = Credentials.from_authorized_user_info(
            json.loads(self.oauth_token_json), SCOPES
        )
        if not creds.valid:
            if not creds.refresh_token:
                raise RuntimeError("Gmail token is invalid and has no refresh token.")
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
                handle.write(self.oauth_client_json)
                credentials_path = Path(handle.name)
            try:
                creds.refresh(Request())
            finally:
                credentials_path.unlink(missing_ok=True)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def search_messages(
        self,
        days: int = 14,
        max_results: int = 100,
        query_extra: str = "",
    ) -> list[EmailMessage]:
        after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y/%m/%d")
        keyword_query = (
            '("application" OR "applied" OR "interview" OR "recruiter" OR '
            '"unfortunately" OR "not moving forward" OR "offer" OR "next step" '
            'OR "thank you for applying")'
        )
        query = f"after:{after} {keyword_query}"
        if query_extra:
            query = f"{query} {query_extra}"

        ids: list[dict[str, str]] = []
        page_token: str | None = None
        while len(ids) < max_results:
            response = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=min(100, max_results - len(ids)),
                    pageToken=page_token,
                    includeSpamTrash=False,
                )
                .execute()
            )
            ids.extend(response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return [self.get_message(item["id"]) for item in ids]

    def get_message(self, message_id: str) -> EmailMessage:
        raw = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = {
            header["name"].lower(): header["value"]
            for header in raw.get("payload", {}).get("headers", [])
        }
        body = self._payload_to_text(raw.get("payload", {}))
        body = html_to_text(body)
        date = _parse_email_date(headers.get("date", ""))
        links = extract_links("\n".join([raw.get("snippet", ""), body]))
        return EmailMessage(
            message_id=raw["id"],
            thread_id=raw.get("threadId", ""),
            sender=headers.get("from", ""),
            subject=headers.get("subject", ""),
            date=date,
            snippet=raw.get("snippet", ""),
            body=body,
            links=links,
        )

    def _payload_to_text(self, payload: dict[str, Any]) -> str:
        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")
        if body_data and mime_type in {"text/plain", "text/html"}:
            return _decode_body(body_data)
        parts = payload.get("parts", [])
        plain: list[str] = []
        html_parts: list[str] = []
        for part in parts:
            text = self._payload_to_text(part)
            if not text:
                continue
            if part.get("mimeType") == "text/html":
                html_parts.append(text)
            else:
                plain.append(text)
        return "\n".join(plain or html_parts)


def _decode_body(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
        "utf-8", errors="replace"
    )


def _parse_email_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
