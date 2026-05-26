from __future__ import annotations

import hashlib
import json
from datetime import timezone

from .classifier import classify_email
from .extract import infer_company, infer_role
from .matcher import already_recorded, match_row
from .models import EmailMessage, NotionRow, Proposal
from .text_utils import truncate


MIN_CONFIDENCE = 0.72


def build_proposals(
    emails: list[EmailMessage],
    rows: list[NotionRow],
    min_confidence: float = MIN_CONFIDENCE,
) -> list[Proposal]:
    proposals: list[Proposal] = []
    for email in emails:
        if already_recorded(email, rows):
            continue
        classification = classify_email(email)
        if not classification or classification.confidence < min_confidence:
            continue

        match = match_row(email, rows)
        company = match.row.company if match.row else infer_company(email, rows)
        role = match.row.role if match.row else infer_role(email, rows, company)
        action = "update" if match.row else "create"
        properties = _properties_for(email, classification.status, company, role, match.row)
        proposal_id = _proposal_id(
            email.message_id,
            action,
            match.row.page_id if match.row else "",
            company,
            role,
            classification.status,
        )
        warnings = []
        if not match.row:
            warnings.append("No matching Notion row found; this would create a new row.")
        elif match.confidence < 0.75:
            warnings.append("Low-confidence Notion row match; review company/role carefully.")
        proposals.append(
            Proposal(
                proposal_id=proposal_id,
                action=action,
                status=classification.status,
                confidence=min(classification.confidence, max(match.confidence, 0.75))
                if match.row
                else classification.confidence,
                company=company,
                role=role,
                email=email,
                classification=classification,
                properties=properties,
                target_page_id=match.row.page_id if match.row else None,
                target_url=f"https://www.notion.so/{match.row.page_id.replace('-', '')}"
                if match.row
                else None,
                match_reason=match.reason,
                warnings=warnings,
            )
        )
    return sorted(proposals, key=lambda item: (item.action, item.company, item.role))


def proposals_to_json(proposals: list[Proposal]) -> str:
    return json.dumps([proposal.to_json() for proposal in proposals], indent=2)


def proposals_to_markdown(proposals: list[Proposal], days: int) -> str:
    if not proposals:
        return (
            "# Gmail -> Notion Job Updates Review\n\n"
            f"No proposed updates from the last {days} days.\n"
        )

    lines = [
        "# Gmail -> Notion Job Updates Review",
        "",
        f"Scanned Gmail messages from the last {days} days.",
        "",
        "Review proposal IDs, then run the **Apply approved Gmail proposals** workflow with a comma-separated list of IDs.",
        "",
        "## Proposed changes",
        "",
    ]
    for proposal in proposals:
        email_date = proposal.email.date.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if proposal.email.date else "unknown date"
        checkbox = f"- [ ] `{proposal.proposal_id}`"
        target = proposal.target_url or "new Notion row"
        lines.extend(
            [
                f"{checkbox} **{proposal.status}**: {proposal.company}"
                + (f" - {proposal.role}" if proposal.role else ""),
                f"  - Action: `{proposal.action}` -> {target}",
                f"  - Confidence: `{proposal.confidence:.2f}`; match: {proposal.match_reason}",
                f"  - Email: {email_date}, from `{proposal.email.sender}`, subject `{proposal.email.subject}`",
                f"  - Evidence: {proposal.classification.evidence}",
                f"  - Properties: `{json.dumps(proposal.properties, sort_keys=True)}`",
            ]
        )
        for warning in proposal.warnings:
            lines.append(f"  - Warning: {warning}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def apply_proposals(proposals: list[Proposal], selected_ids: set[str], notion_client) -> list[Proposal]:
    selected = [proposal for proposal in proposals if proposal.proposal_id in selected_ids]
    missing = selected_ids - {proposal.proposal_id for proposal in selected}
    if missing:
        raise RuntimeError(f"Proposal IDs not found in current scan: {', '.join(sorted(missing))}")
    for proposal in selected:
        if proposal.action == "update":
            if not proposal.target_page_id:
                raise RuntimeError(f"Update proposal {proposal.proposal_id} has no target page.")
            notion_client.update_page(proposal.target_page_id, proposal.properties)
        elif proposal.action == "create":
            notion_client.create_page(proposal.properties)
        else:
            raise RuntimeError(f"Unsupported proposal action: {proposal.action}")
    return selected


def _properties_for(
    email: EmailMessage,
    status: str,
    company: str,
    role: str,
    row: NotionRow | None,
) -> dict[str, str]:
    source_note = _source_note(email, status)
    if row:
        notes = "\n".join(part for part in [row.notes, source_note] if part).strip()
        properties = {
            "Status": status,
            "Notes": truncate(notes, 1900),
        }
        if status in {"Recruiter screen", "Interviewing"}:
            properties["Next step"] = "Respond / schedule interview"
        if status == "Offer":
            properties["Next step"] = "Review offer"
        return properties

    applied = ""
    if status == "Applied" and email.date:
        applied = f"{email.date.month}/{email.date.day}"
    properties = {
        "Company": company,
        "Role": role,
        "Status": status,
        "Applied": applied,
        "Next step": "Respond / schedule interview"
        if status in {"Recruiter screen", "Interviewing"}
        else "Review offer"
        if status == "Offer"
        else "",
        "Next step date": "",
        "Link": email.links[0] if email.links else "",
        "Notes": source_note,
    }
    return properties


def _source_note(email: EmailMessage, status: str) -> str:
    date = email.date.date().isoformat() if email.date else "unknown date"
    return truncate(
        f"[gmail:{email.message_id} thread:{email.thread_id}] {date} {status}: "
        f"{email.sender} - {email.subject}. Evidence: {email.snippet or email.body}",
        1200,
    )


def _proposal_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
