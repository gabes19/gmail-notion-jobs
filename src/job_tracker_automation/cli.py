from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .github_issue import GitHubIssueClient
from .gmail_client import GmailClient
from .notion_client import NotionClient
from .proposals import (
    apply_proposals,
    build_proposals,
    proposals_to_json,
    proposals_to_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gmail-notion-jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan Gmail and produce review proposals.")
    _add_scan_args(scan)
    scan.add_argument("--write-issue", action="store_true", help="Create/update the GitHub review issue.")
    scan.add_argument("--json-output", type=Path, help="Write proposals JSON to this path.")
    scan.add_argument("--markdown-output", type=Path, help="Write review Markdown to this path.")
    scan.add_argument("--quiet", action="store_true", help="Do not print proposal details to stdout.")

    apply = subparsers.add_parser("apply", help="Apply selected proposal IDs to Notion.")
    _add_scan_args(apply)
    apply.add_argument("--proposal-ids", required=True, help="Comma-separated proposal IDs to apply.")
    apply.add_argument("--dry-run", action="store_true", help="Print selected proposals without mutating Notion.")

    args = parser.parse_args(argv)
    settings = Settings.from_env()

    if args.command == "scan":
        return _scan(args, settings)
    if args.command == "apply":
        return _apply(args, settings)
    parser.error(f"Unknown command: {args.command}")
    return 2


def _add_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--days", type=int, default=14, help="Gmail lookback window.")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum Gmail messages to inspect.")
    parser.add_argument("--query-extra", default="", help="Extra Gmail query terms.")
    parser.add_argument("--min-confidence", type=float, default=0.72, help="Minimum classification confidence.")


def _scan(args: argparse.Namespace, settings: Settings) -> int:
    settings.require_scan()
    proposals = _collect_proposals(args, settings)
    markdown = proposals_to_markdown(proposals, args.days)
    json_payload = proposals_to_json(proposals)

    if args.markdown_output:
        args.markdown_output.write_text(markdown, encoding="utf-8")
    if args.json_output:
        args.json_output.write_text(json_payload, encoding="utf-8")

    if args.quiet:
        print(f"Generated {len(proposals)} proposal(s).")
    else:
        print(markdown)
    if args.write_issue:
        settings.require_github()
        issue_url = GitHubIssueClient(
            settings.github_token, settings.github_repository
        ).upsert_issue(settings.review_issue_title, markdown)
        print(f"Review issue: {issue_url}")
    return 0


def _apply(args: argparse.Namespace, settings: Settings) -> int:
    settings.require_scan()
    selected_ids = {
        item.strip() for item in args.proposal_ids.split(",") if item.strip()
    }
    if not selected_ids:
        raise RuntimeError("--proposal-ids must include at least one ID.")

    proposals = _collect_proposals(args, settings)
    selected = [proposal for proposal in proposals if proposal.proposal_id in selected_ids]
    if args.dry_run:
        print(proposals_to_json(selected))
        missing = selected_ids - {proposal.proposal_id for proposal in selected}
        if missing:
            raise RuntimeError(f"Proposal IDs not found in current scan: {', '.join(sorted(missing))}")
        return 0

    notion = NotionClient(
        settings.notion_token,
        settings.notion_data_source_id,
        settings.notion_version,
    )
    applied = apply_proposals(proposals, selected_ids, notion)
    print(f"Applied {len(applied)} proposal(s): {', '.join(item.proposal_id for item in applied)}")
    return 0


def _collect_proposals(args: argparse.Namespace, settings: Settings):
    gmail = GmailClient(settings.google_oauth_client_json, settings.google_oauth_token_json)
    notion = NotionClient(
        settings.notion_token,
        settings.notion_data_source_id,
        settings.notion_version,
    )
    rows = notion.list_rows()
    emails = gmail.search_messages(
        days=args.days,
        max_results=args.max_results,
        query_extra=args.query_extra,
    )
    return build_proposals(emails, rows, min_confidence=args.min_confidence)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
