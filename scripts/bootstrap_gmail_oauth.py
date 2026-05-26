from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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

    flow = InstalledAppFlow.from_client_secrets_file(str(args.credentials), SCOPES)
    creds = flow.run_local_server(port=0)
    args.token_output.write_text(creds.to_json(), encoding="utf-8")

    client_json = json.dumps(json.loads(args.credentials.read_text(encoding="utf-8")))
    token_json = json.dumps(json.loads(args.token_output.read_text(encoding="utf-8")))
    print("Add these GitHub repository secrets:")
    print(f"GOOGLE_OAUTH_CLIENT_JSON={client_json}")
    print(f"GOOGLE_OAUTH_TOKEN_JSON={token_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
