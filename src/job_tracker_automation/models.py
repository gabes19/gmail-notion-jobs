from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EmailMessage:
    message_id: str
    thread_id: str
    sender: str
    subject: str
    date: datetime | None
    snippet: str
    body: str
    links: tuple[str, ...] = ()

    @property
    def searchable_text(self) -> str:
        return "\n".join([self.sender, self.subject, self.snippet, self.body])


@dataclass(frozen=True)
class Classification:
    status: str
    confidence: float
    evidence: str
    matched_rules: tuple[str, ...] = ()
    next_step: str = ""
    next_step_date: str = ""


@dataclass(frozen=True)
class NotionRow:
    page_id: str
    company: str
    role: str
    status: str
    applied: str
    next_step: str
    next_step_date: str
    link: str
    notes: str


@dataclass(frozen=True)
class RowMatch:
    row: NotionRow | None
    confidence: float
    reason: str


@dataclass
class Proposal:
    proposal_id: str
    action: str
    status: str
    confidence: float
    company: str
    role: str
    email: EmailMessage
    classification: Classification
    properties: dict[str, str]
    target_page_id: str | None = None
    target_url: str | None = None
    match_reason: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.proposal_id,
            "action": self.action,
            "status": self.status,
            "confidence": self.confidence,
            "company": self.company,
            "role": self.role,
            "target_page_id": self.target_page_id,
            "target_url": self.target_url,
            "match_reason": self.match_reason,
            "warnings": self.warnings,
            "properties": self.properties,
            "email": {
                "message_id": self.email.message_id,
                "thread_id": self.email.thread_id,
                "sender": self.email.sender,
                "subject": self.email.subject,
                "date": self.email.date.isoformat() if self.email.date else None,
                "snippet": self.email.snippet,
            },
            "classification": {
                "evidence": self.classification.evidence,
                "matched_rules": list(self.classification.matched_rules),
                "next_step": self.classification.next_step,
                "next_step_date": self.classification.next_step_date,
            },
        }
