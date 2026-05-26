from __future__ import annotations

from .models import EmailMessage, NotionRow, RowMatch
from .text_utils import normalize_text, token_set


def match_row(email: EmailMessage, rows: list[NotionRow]) -> RowMatch:
    text = normalize_text(email.searchable_text)
    scored: list[tuple[float, str, NotionRow]] = []
    for row in rows:
        if not row.company:
            continue
        company_norm = normalize_text(row.company)
        if not company_norm or company_norm not in text:
            continue
        score = 0.65
        reasons = ["company"]
        if row.role:
            role_norm = normalize_text(row.role)
            role_tokens = token_set(row.role)
            text_tokens = token_set(email.searchable_text)
            role_score = len(role_tokens & text_tokens) / len(role_tokens) if role_tokens else 0
            if role_norm in text or role_score >= 0.5:
                score += 0.25
                reasons.append("role")
        if row.link and any(link in email.searchable_text for link in _extract_urls(row.link)):
            score += 0.15
            reasons.append("job link")
        scored.append((min(score, 0.99), ", ".join(reasons), row))

    if not scored:
        return RowMatch(row=None, confidence=0.0, reason="no matching Notion row")
    scored.sort(key=lambda item: item[0], reverse=True)
    score, reason, row = scored[0]
    return RowMatch(row=row, confidence=score, reason=reason)


def already_recorded(email: EmailMessage, rows: list[NotionRow]) -> bool:
    needle = f"gmail:{email.message_id}"
    return any(needle in row.notes for row in rows)


def _extract_urls(value: str) -> list[str]:
    return [part.strip("[]()") for part in value.split() if part.startswith("http")]
