from __future__ import annotations

import re
from email.utils import parseaddr

from .models import EmailMessage, NotionRow
from .text_utils import normalize_text, sender_name, token_set, truncate


COMPANY_SUFFIXES = {
    "careers",
    "jobs",
    "recruiting",
    "recruiter",
    "talent",
    "team",
    "workday",
    "greenhouse",
    "ashby",
    "lever",
}


def infer_company(email: EmailMessage, rows: list[NotionRow]) -> str:
    text = normalize_text(email.searchable_text)
    matches = [
        row.company
        for row in rows
        if row.company and normalize_text(row.company) in text
    ]
    if matches:
        return sorted(matches, key=len, reverse=True)[0]

    patterns = (
        r"\bat\s+([A-Z][A-Za-z0-9&.\- ]{2,45})",
        r"\bfrom\s+([A-Z][A-Za-z0-9&.\- ]{2,45})",
        r"\bwith\s+([A-Z][A-Za-z0-9&.\- ]{2,45})",
    )
    for pattern in patterns:
        match = re.search(pattern, email.searchable_text)
        if match:
            candidate = _clean_company(match.group(1))
            if candidate:
                return candidate

    name, address = parseaddr(email.sender)
    display = _clean_company(name)
    if display and normalize_text(display) not in COMPANY_SUFFIXES:
        return display
    if "@" in address:
        domain = address.split("@", 1)[1].split(".", 1)[0]
        if domain and normalize_text(domain) not in COMPANY_SUFFIXES:
            return domain.replace("-", " ").title()
    return _clean_company(sender_name(email.sender)) or "Unknown Company"


def infer_role(email: EmailMessage, rows: list[NotionRow], company: str = "") -> str:
    text_tokens = token_set(email.searchable_text)
    candidates = [
        row.role
        for row in rows
        if row.role and len(token_set(row.role) & text_tokens) >= 2
    ]
    if candidates:
        return sorted(candidates, key=len, reverse=True)[0]

    patterns = (
        r"(?:for|regarding|about)\s+(?:the\s+)?([A-Z][A-Za-z0-9,&/\- ]{4,80}?)(?:\s+(?:role|position|opening)|[.,\n]|$)",
        r"([A-Z][A-Za-z0-9,&/\- ]{4,80}?)\s+(?:role|position|opening)",
    )
    for pattern in patterns:
        match = re.search(pattern, email.searchable_text)
        if match:
            candidate = _clean_role(match.group(1), company)
            if candidate:
                return candidate
    return ""


def _clean_company(value: str) -> str:
    value = re.sub(r"[<(\[].*", "", value)
    value = re.sub(r"\b(careers|jobs|recruiting|talent|team)\b", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" -:,.")
    words = value.split()
    while words and normalize_text(words[-1]) in COMPANY_SUFFIXES:
        words.pop()
    return truncate(" ".join(words), 80)


def _clean_role(value: str, company: str) -> str:
    value = re.sub(re.escape(company), "", value, flags=re.I) if company else value
    value = re.sub(r"\s+", " ", value).strip(" -:,.")
    return truncate(value, 100)
