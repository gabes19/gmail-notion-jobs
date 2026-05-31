from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests

from .models import NotionRow


REQUIRED_DATA_SOURCE_PROPERTIES = frozenset({"Company", "Role", "Status", "Notes"})


class NotionConfigurationError(RuntimeError):
    pass


class NotionClient:
    def __init__(
        self,
        token: str,
        data_source_id: str,
        notion_version: str = "2025-09-03",
    ) -> None:
        self.token = token
        self.original_data_source_id = data_source_id.strip()
        self.data_source_id = _normalize_notion_id(data_source_id)
        self.notion_version = notion_version
        self._tried_database_resolution = False
        self._tried_data_source_discovery = False
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": notion_version,
                "Content-Type": "application/json",
            }
        )

    def list_rows(self) -> list[NotionRow]:
        rows: list[NotionRow] = []
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            response = self._query_data_source(payload)
            response.raise_for_status()
            data = response.json()
            rows.extend(_page_to_row(page) for page in data.get("results", []))
            if not data.get("has_more"):
                return rows
            cursor = data.get("next_cursor")

    def update_page(self, page_id: str, properties: dict[str, str]) -> None:
        response = self.session.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            json={"properties": _notion_properties(properties)},
            timeout=30,
        )
        response.raise_for_status()

    def create_page(self, properties: dict[str, str]) -> str:
        self._prepare_data_source_parent()
        response = self.session.post(
            "https://api.notion.com/v1/pages",
            json={
                "parent": {"type": "data_source_id", "data_source_id": self.data_source_id},
                "properties": _notion_properties(properties),
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["id"]

    def _query_data_source(self, payload: dict[str, Any]) -> requests.Response:
        response = self.session.post(
            f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",
            json=payload,
            timeout=30,
        )
        if response.status_code != 404:
            return response

        self._resolve_database_id_if_present()
        response = self.session.post(
            f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",
            json=payload,
            timeout=30,
        )
        if response.status_code != 404:
            return response

        self._discover_data_source_by_schema()
        response = self.session.post(
            f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",
            json=payload,
            timeout=30,
        )
        if response.status_code == 404:
            raise NotionConfigurationError(
                "Notion could not find the configured data source. Set "
                "NOTION_DATA_SOURCE_ID to the Applications data source ID, or to a "
                "database ID whose first data source is shared with your Notion "
                "integration. If the ID is correct, share the original Applications "
                "database with the same integration token used by NOTION_TOKEN."
            )
        return response

    def _prepare_data_source_parent(self) -> None:
        response = self.session.get(
            f"https://api.notion.com/v1/data_sources/{self.data_source_id}",
            timeout=30,
        )
        if response.status_code != 404:
            response.raise_for_status()
            return
        if not self._resolve_database_id_if_present():
            self._discover_data_source_by_schema()

    def _resolve_database_id_if_present(self) -> bool:
        if self._tried_database_resolution:
            return False
        self._tried_database_resolution = True

        response = self.session.get(
            f"https://api.notion.com/v1/databases/{self.data_source_id}",
            timeout=30,
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()

        data_sources = response.json().get("data_sources", [])
        if not data_sources:
            raise NotionConfigurationError(
                "Notion found the configured database, but it did not return any "
                "data sources. Copy the Applications data source ID from Notion's "
                "Manage data sources menu and use it for NOTION_DATA_SOURCE_ID."
            )
        self.data_source_id = _normalize_notion_id(data_sources[0]["id"])
        return True

    def _discover_data_source_by_schema(self) -> bool:
        if self._tried_data_source_discovery:
            return False
        self._tried_data_source_discovery = True

        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {
                "filter": {"property": "object", "value": "data_source"},
                "page_size": 100,
            }
            if cursor:
                payload["start_cursor"] = cursor

            response = self.session.post(
                "https://api.notion.com/v1/search",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            for result in data.get("results", []):
                data_source = result
                if "properties" not in data_source:
                    data_source = self._retrieve_data_source(result["id"])
                if _has_required_properties(data_source):
                    self.data_source_id = _normalize_notion_id(data_source["id"])
                    return True

            if not data.get("has_more"):
                return False
            cursor = data.get("next_cursor")

    def _retrieve_data_source(self, data_source_id: str) -> dict[str, Any]:
        response = self.session.get(
            f"https://api.notion.com/v1/data_sources/{_normalize_notion_id(data_source_id)}",
            timeout=30,
        )
        response.raise_for_status()
        return response.json()


def _page_to_row(page: dict[str, Any]) -> NotionRow:
    props = page.get("properties", {})
    return NotionRow(
        page_id=page["id"],
        company=_read_prop(props.get("Company")),
        role=_read_prop(props.get("Role")),
        status=_read_prop(props.get("Status")),
        applied=_read_prop(props.get("Applied")),
        next_step=_read_prop(props.get("Next step")),
        next_step_date=_read_prop(props.get("Next step date")),
        link=_read_prop(props.get("Link")),
        notes=_read_prop(props.get("Notes")),
    )


def _read_prop(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    prop_type = prop.get("type")
    if prop_type == "title":
        return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    if prop_type == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if prop_type == "url":
        return prop.get("url") or ""
    if prop_type == "status":
        return (prop.get("status") or {}).get("name", "")
    if prop_type == "select":
        return (prop.get("select") or {}).get("name", "")
    if prop_type == "date":
        return (prop.get("date") or {}).get("start", "")
    return str(prop.get(prop_type, "") or "")


def _normalize_notion_id(value: str) -> str:
    notion_id = value.strip().replace("collection://", "")
    parsed = urlparse(notion_id)
    if parsed.scheme and parsed.netloc:
        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            notion_id = path_parts[-1]

    notion_id = notion_id.split("?", 1)[0].split("#", 1)[0]
    match = re.search(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        notion_id,
    )
    if match:
        return match.group(1)

    match = re.search(r"([0-9a-fA-F]{32})", notion_id)
    if match:
        return match.group(1)
    return notion_id


def _has_required_properties(data_source: dict[str, Any]) -> bool:
    return REQUIRED_DATA_SOURCE_PROPERTIES.issubset(data_source.get("properties", {}))


def _notion_properties(properties: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in properties.items():
        if key == "Company":
            payload[key] = {"title": [{"text": {"content": value}}]}
        else:
            payload[key] = {"rich_text": [{"text": {"content": value}}]} if value else {"rich_text": []}
    return payload
