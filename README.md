# Gmail to Notion Job Tracker

Review-first automation that scans Gmail for job application updates and proposes changes for your Notion job board.

## What it does

- Scans recent Gmail messages for application confirmations, rejections, interviews, offers, and hold/fill notices.
- Matches emails to the Notion `Applications` data source configured by `NOTION_DATA_SOURCE_ID`.
- Opens or updates a GitHub issue named `Gmail -> Notion Job Updates Review`.
- Applies only the proposal IDs you explicitly pass to the manual GitHub Actions workflow.

## Setup

### Local preparation

1. Create a Google OAuth desktop client with Gmail API enabled.
2. Download it as `credentials.json`.
3. Install locally:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

4. Bootstrap Gmail OAuth:

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_gmail_oauth.py --credentials credentials.json --token-output token.json
```

5. Add these GitHub repository secrets:

- `GOOGLE_OAUTH_CLIENT_JSON`
- `GOOGLE_OAUTH_TOKEN_JSON`
- `NOTION_TOKEN`
- `NOTION_DATA_SOURCE_ID`

Optional repository variable:

- `NOTION_VERSION`, default `2025-09-03`

### GitHub deployment

From this directory:

```powershell
git init
git add .
git commit -m "Add Gmail Notion job tracker automation"
gh repo create gmail-notion-jobs --private --source . --remote origin --push
```

Then confirm the repository has Actions enabled and add the secrets above under **Settings -> Secrets and variables -> Actions**.

## Workflows

- `CI` runs tests on push, pull requests, and manual dispatch.
- `Scan Gmail job updates` runs daily at `13:00 UTC` and can also be run manually.
- `Apply approved Gmail proposals` takes comma-separated proposal IDs from the review issue.
- Use the apply workflow's `dry_run` option first when you want to inspect selected payloads without changing Notion.

## Local commands

```powershell
gmail-notion-jobs scan --days 14 --max-results 100 --markdown-output review.md --json-output proposals.json
gmail-notion-jobs apply --proposal-ids abc123def456 --dry-run
```

For local runs, provide environment variables from `.env.example`.
