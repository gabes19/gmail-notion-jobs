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

If Google shows `Error 403: access_denied` and says the app has not completed verification, add the Gmail account you are authorizing as a test user in Google Cloud Console:

1. Open **Google Cloud Console -> APIs & Services -> OAuth consent screen**.
2. Make sure the app is configured for the correct audience.
   - Use **External** for a personal Gmail account.
   - Use **Internal** only for accounts in the same Google Workspace.
3. Under **Test users**, add the exact Google account email you will sign in with.
4. Save, wait a minute, then rerun the bootstrap command.

For a personal automation, Google verification is not required while you are in Testing mode and your account is listed as a test user.

5. Add these GitHub environment secrets under **Settings -> Environments -> env -> Environment secrets**:

- `GOOGLE_OAUTH_CLIENT_JSON`
- `GOOGLE_OAUTH_TOKEN_JSON`
- `NOTION_TOKEN`
- `NOTION_DATA_SOURCE_ID`

Optional repository or environment variable:

- `NOTION_VERSION`, default `2025-09-03`

### Notion setup

Create a Notion connection for the workspace that owns your job board:

1. Open [Notion Developers](https://www.notion.so/developers).
2. Create a new **internal connection** for the same workspace that contains your `Job Search` page.
3. In the connection's **Capabilities** settings, allow the minimum access this automation needs:
   - Read content
   - Insert content
   - Update content
4. Copy the internal connection token. Use it as the GitHub secret `NOTION_TOKEN`.
5. Give the connection access to your job board using either Notion-supported path:
   - Preferred from the developer portal: open the connection's **Content access** tab and add the `Job Search` page or the `Applications` database.
   - From Notion: open the `Job Search` page, click the `...` menu, choose `Add connections`, search for your connection, and confirm access to the page and child pages.
6. Set `NOTION_DATA_SOURCE_ID` to the data source ID for the `Applications` database. A database ID from the Notion URL also works if the integration can retrieve that database and it has a data source. Keep this only in GitHub Secrets, not in source code.

If the connection does not appear in `Add connections`, confirm:

- You created it in the same workspace as the job board.
- You are a workspace owner, or a workspace owner has created/approved the connection.
- The page is not in a teamspace where you lack permission to manage connections.
- You are looking under `...` -> `Add connections`, not the old sharing/invite UI.

### GitHub deployment

From this directory:

```powershell
git init
git add .
git commit -m "Add Gmail Notion job tracker automation"
gh repo create gmail-notion-jobs --private --source . --remote origin --push
```

Then confirm the repository has Actions enabled and add the secrets above under **Settings -> Environments -> env -> Environment secrets**.

## Workflows

- `CI` runs tests on push, pull requests, and manual dispatch.
- `Scan Gmail job updates` runs daily at `13:00 UTC` and can also be run manually.
- `Apply approved Gmail proposals` takes comma-separated proposal IDs from the review issue.
- Use the apply workflow's `dry_run` option first when you want to inspect selected payloads without changing Notion.

### Public repository warning

The source code is safe to publish, but scan outputs can contain private email details such as sender, subject, snippet, company, and inferred status.

For a public repository:

- Keep `PUBLISH_REVIEW_ISSUE` unset or set to `false`.
- Keep `PUBLISH_REVIEW_ARTIFACT` unset or set to `false`.
- Run scans locally when you need to inspect proposal details, or keep the GitHub repository private if you want review issues/artifacts in GitHub.

Only set `PUBLISH_REVIEW_ISSUE=true` or `PUBLISH_REVIEW_ARTIFACT=true` in GitHub Actions variables if the repository is private or you are comfortable exposing proposal details to repository readers.

## Local commands

```powershell
gmail-notion-jobs scan --days 14 --max-results 100 --markdown-output review.md --json-output proposals.json
gmail-notion-jobs apply --proposal-ids abc123def456 --dry-run
```

For local runs, provide environment variables from `.env.example`.
