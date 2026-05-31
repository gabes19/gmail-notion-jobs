from __future__ import annotations

from typing import Any

import requests

from job_tracker_automation.notion_client import (
    NotionClient,
    _normalize_notion_id,
    _notion_properties,
    _read_prop,
)


def test_notion_properties_use_title_for_company_and_rich_text_for_text_fields() -> None:
    payload = _notion_properties({"Company": "Acme Analytics", "Status": "Rejected", "Notes": ""})

    assert payload["Company"]["title"][0]["text"]["content"] == "Acme Analytics"
    assert payload["Status"]["rich_text"][0]["text"]["content"] == "Rejected"
    assert payload["Notes"]["rich_text"] == []


def test_read_notion_rich_text_property() -> None:
    assert (
        _read_prop({"type": "rich_text", "rich_text": [{"plain_text": "Applied"}]})
        == "Applied"
    )


def test_normalizes_full_notion_url_to_id() -> None:
    assert (
        _normalize_notion_id(
            "https://www.notion.so/workspace/Applications-248104cd477e80afbc30000bd28de8f9?v=123"
        )
        == "248104cd477e80afbc30000bd28de8f9"
    )


def test_list_rows_resolves_database_id_to_first_data_source() -> None:
    client = NotionClient("token", "database-id")
    session = FakeSession(
        [
            FakeResponse(404, {}),
            FakeResponse(200, {"data_sources": [{"id": "data-source-id"}]}),
            FakeResponse(200, {"results": [], "has_more": False}),
        ]
    )
    client.session = session

    assert client.list_rows() == []
    assert session.requests == [
        ("POST", "https://api.notion.com/v1/data_sources/database-id/query"),
        ("GET", "https://api.notion.com/v1/databases/database-id"),
        ("POST", "https://api.notion.com/v1/data_sources/data-source-id/query"),
    ]


def test_list_rows_discovers_shared_data_source_by_schema() -> None:
    client = NotionClient("token", "wrong-id")
    session = FakeSession(
        [
            FakeResponse(404, {}),
            FakeResponse(404, {}),
            FakeResponse(404, {}),
            FakeResponse(
                200,
                {
                    "results": [
                        {
                            "id": "found-data-source-id",
                            "properties": {
                                "Company": {},
                                "Role": {},
                                "Status": {},
                                "Notes": {},
                            },
                        }
                    ],
                    "has_more": False,
                },
            ),
            FakeResponse(200, {"results": [], "has_more": False}),
        ]
    )
    client.session = session

    assert client.list_rows() == []
    assert session.requests == [
        ("POST", "https://api.notion.com/v1/data_sources/wrong-id/query"),
        ("GET", "https://api.notion.com/v1/databases/wrong-id"),
        ("POST", "https://api.notion.com/v1/data_sources/wrong-id/query"),
        ("POST", "https://api.notion.com/v1/search"),
        ("POST", "https://api.notion.com/v1/data_sources/found-data-source-id/query"),
    ]


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str]] = []

    def post(self, url: str, **_: Any) -> FakeResponse:
        self.requests.append(("POST", url))
        return self.responses.pop(0)

    def get(self, url: str, **_: Any) -> FakeResponse:
        self.requests.append(("GET", url))
        return self.responses.pop(0)
