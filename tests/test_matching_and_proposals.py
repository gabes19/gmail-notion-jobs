from __future__ import annotations

from datetime import datetime, timezone

from job_tracker_automation.matcher import match_row
from job_tracker_automation.models import EmailMessage, NotionRow
from job_tracker_automation.proposals import build_proposals


def email(
    message_id: str = "m1",
    subject: str = "Acme Analytics Data Analyst Intern application",
    body: str = "Thank you for applying to the Data Analyst Intern role at Acme Analytics.",
    sender: str = "Acme Analytics Careers <careers@acme.example>",
) -> EmailMessage:
    return EmailMessage(
        message_id=message_id,
        thread_id="t1",
        sender=sender,
        subject=subject,
        date=datetime(2026, 5, 26, tzinfo=timezone.utc),
        snippet=body,
        body=body,
        links=("https://example.com/job",),
    )


def row(notes: str = "") -> NotionRow:
    return NotionRow(
        page_id="11111111-2222-3333-4444-555555555555",
        company="Acme Analytics",
        role="Data Analyst Intern",
        status="Applied",
        applied="5/13",
        next_step="",
        next_step_date="",
        link="",
        notes=notes,
    )


def test_matches_company_and_role() -> None:
    match = match_row(email(), [row()])

    assert match.row is not None
    assert match.row.company == "Acme Analytics"
    assert match.confidence >= 0.75


def test_builds_update_proposal_for_existing_row() -> None:
    proposals = build_proposals([email()], [row()])

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.action == "update"
    assert proposal.properties["Status"] == "Applied"
    assert "gmail:m1" in proposal.properties["Notes"]


def test_skips_duplicate_message_in_notes() -> None:
    proposals = build_proposals([email()], [row(notes="[gmail:m1 thread:t1] already handled")])

    assert proposals == []


def test_builds_create_proposal_for_unmatched_email() -> None:
    proposals = build_proposals(
        [
            email(
                subject="Application received at Northstar Robotics",
                body="Thank you for applying to the Software Engineering Intern role at Northstar Robotics.",
                sender="Northstar Robotics Careers <careers@northstar.example>",
            )
        ],
        [row()],
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.action == "create"
    assert proposal.company == "Northstar Robotics"
    assert proposal.properties["Company"] == "Northstar Robotics"
