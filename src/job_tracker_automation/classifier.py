from __future__ import annotations

import re

from .models import Classification, EmailMessage
from .text_utils import normalize_text, truncate


RULES: dict[str, tuple[tuple[str, float], ...]] = {
    "Rejected": (
        ("not moving forward", 0.98),
        ("decided to move forward with other candidates", 0.98),
        ("we will not be moving forward", 0.98),
        ("unfortunately", 0.86),
        ("after careful consideration", 0.86),
        ("not selected", 0.9),
        ("pursue other candidates", 0.92),
    ),
    "Offer": (
        ("congratulations", 0.88),
        ("pleased to offer", 0.98),
        ("offer letter", 0.96),
        ("extend an offer", 0.98),
    ),
    "Recruiter screen": (
        ("recruiter screen", 0.96),
        ("phone screen", 0.9),
        ("initial screen", 0.86),
        ("introductory call", 0.84),
    ),
    "Interviewing": (
        ("schedule an interview", 0.95),
        ("invite you to interview", 0.95),
        ("next step", 0.82),
        ("availability", 0.72),
        ("meet with", 0.72),
        ("technical interview", 0.92),
    ),
    "On hold": (
        ("on hold", 0.92),
        ("paused", 0.86),
        ("position has been filled", 0.88),
        ("role has been filled", 0.88),
        ("no longer available", 0.9),
    ),
    "Applied": (
        ("application received", 0.96),
        ("we received your application", 0.96),
        ("thank you for applying", 0.94),
        ("thanks for applying", 0.9),
        ("your application has been submitted", 0.94),
    ),
}

STATUS_PRIORITY = {
    "Offer": 6,
    "Rejected": 5,
    "Recruiter screen": 4,
    "Interviewing": 3,
    "On hold": 2,
    "Applied": 1,
}


def classify_email(email: EmailMessage) -> Classification | None:
    text = normalize_text(email.searchable_text)
    candidates: list[Classification] = []
    for status, rules in RULES.items():
        matched = []
        score = 0.0
        for phrase, confidence in rules:
            if normalize_text(phrase) in text:
                matched.append(phrase)
                score = max(score, confidence)
        if matched:
            score = min(0.99, score + 0.02 * (len(matched) - 1))
            candidates.append(
                Classification(
                    status=status,
                    confidence=score,
                    evidence=_evidence(email.searchable_text, matched[0]),
                    matched_rules=tuple(matched),
                    next_step=_next_step(status),
                )
            )
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (item.confidence, STATUS_PRIORITY[item.status]),
        reverse=True,
    )[0]


def _evidence(text: str, phrase: str) -> str:
    match = re.search(re.escape(phrase), text, flags=re.IGNORECASE)
    if not match:
        return truncate(text)
    start = max(match.start() - 90, 0)
    end = min(match.end() + 140, len(text))
    return truncate(text[start:end])


def _next_step(status: str) -> str:
    if status in {"Recruiter screen", "Interviewing"}:
        return "Respond / schedule interview"
    if status == "Offer":
        return "Review offer"
    return ""
