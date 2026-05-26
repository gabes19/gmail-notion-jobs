from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a Gmail OAuth token JSON for GitHub Actions."
    )
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        type=Path,
        help="Downloaded Google OAuth desktop client JSON.",
    )
    parser.add_argument(
        "--token-output",
        default="token.json",
        type=Path,
        help="Where to write the authorized token JSON.",
    )
    args = parser.parse_args()

    credentials_path = _resolve_input_path(args.credentials)
    token_output_path = _resolve_output_path(args.token_output)

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_output_path.write_text(creds.to_json(), encoding="utf-8")

    client_json = json.dumps(json.loads(credentials_path.read_text(encoding="utf-8")))
    token_json = json.dumps(json.loads(token_output_path.read_text(encoding="utf-8")))
    print("Add these GitHub repository secrets:")
    print(f"GOOGLE_OAUTH_CLIENT_JSON={client_json}")
    print(f"GOOGLE_OAUTH_TOKEN_JSON={token_json}")
    return 0


def _resolve_input_path(path: Path) -> Path:
    candidates = [path]
    if not path.is_absolute():
        candidates.extend(
            [
                REPO_ROOT / path,
                REPO_ROOT / path.name,
                Path.cwd() / path,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    checked = "\n  - ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        "Could not find the Gmail OAuth credentials file. Checked:\n"
        f"  - {checked}\n"
        "Put credentials.json in the repo root or pass "
        "--credentials C:\\path\\to\\credentials.json."
    )


def _resolve_output_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


if __name__ == "__main__":
    raise SystemExit(main())
