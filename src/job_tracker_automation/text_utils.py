from __future__ import annotations

import html
import re
import unicodedata
from email.utils import parseaddr


STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "for",
    "in",
    "intern",
    "internship",
    "of",
    "role",
    "the",
    "to",
}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def token_set(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if token not in STOPWORDS}


def html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</p>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"[ \t\r\f\v]+", " ", value).strip()


def truncate(value: str, limit: int = 280) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def sender_name(sender: str) -> str:
    name, address = parseaddr(sender)
    if name:
        return name
    domain = address.split("@")[-1] if "@" in address else sender
    base = domain.split(".")[0]
    return base.replace("-", " ").replace("_", " ").title()


def extract_links(text: str) -> tuple[str, ...]:
    links = re.findall(r"https?://[^\s<>)\"']+", text)
    clean = []
    for link in links:
        link = link.rstrip(".,;]")
        if link not in clean:
            clean.append(link)
    return tuple(clean)


def overlap_score(left: str, right: str) -> float:
    left_tokens = token_set(left)
    right_tokens = token_set(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    return overlap / max(len(left_tokens), len(right_tokens))
