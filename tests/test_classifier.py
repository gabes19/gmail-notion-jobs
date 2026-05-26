from __future__ import annotations

from datetime import datetime, timezone

from job_tracker_automation.classifier import classify_email
from job_tracker_automation.models import EmailMessage


def message(subject: str, body: str) -> EmailMessage:
    return EmailMessage(
        message_id="m1",
        thread_id="t1",
        sender="Recruiting <jobs@example.com>",
        subject=subject,
        date=datetime(2026, 5, 26, tzinfo=timezone.utc),
        snippet=body[:80],
        body=body,
    )


def test_classifies_rejection() -> None:
    result = classify_email(
        message("Your application", "Unfortunately, we will not be moving forward.")
    )

    assert result is not None
    assert result.status == "Rejected"
    assert result.confidence >= 0.86


def test_classifies_application_confirmation() -> None:
    result = classify_email(
        message("Thanks", "Thank you for applying. We received your application.")
    )

    assert result is not None
    assert result.status == "Applied"
    assert result.confidence >= 0.94


def test_ignores_unrelated_email() -> None:
    assert classify_email(message("Newsletter", "Here are this week's updates.")) is None
