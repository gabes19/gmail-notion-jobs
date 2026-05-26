from __future__ import annotations

from typing import Any

import requests

from .models import NotionRow


class NotionClient:
    def __init__(
        self,
        token: str,
        data_source_id: str,
        notion_version: str = "2025-09-03",
    ) -> None:
        self.token = token
        self.data_source_id = data_source_id.replace("collection://", "")
        self.notion_version = notion_version
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
            response = self.session.post(
                f"https://api.notion.com/v1/data_sources/{self.data_source_id}/query",
                json=payload,
                timeout=30,
            )
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


def _notion_properties(properties: dict[str, str]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in properties.items():
        if key == "Company":
            payload[key] = {"title": [{"text": {"content": value}}]}
        else:
            payload[key] = {"rich_text": [{"text": {"content": value}}]} if value else {"rich_text": []}
    return payload
