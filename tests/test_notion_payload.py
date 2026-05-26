from __future__ import annotations

from job_tracker_automation.notion_client import _notion_properties, _read_prop


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
