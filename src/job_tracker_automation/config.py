from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_NOTION_VERSION = "2025-09-03"
REVIEW_ISSUE_TITLE = "Gmail -> Notion Job Updates Review"


@dataclass(frozen=True)
class Settings:
    google_oauth_client_json: str
    google_oauth_token_json: str
    notion_token: str
    notion_data_source_id: str
    notion_version: str = DEFAULT_NOTION_VERSION
    github_token: str = ""
    github_repository: str = ""
    review_issue_title: str = REVIEW_ISSUE_TITLE

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            google_oauth_client_json=os.environ.get("GOOGLE_OAUTH_CLIENT_JSON", ""),
            google_oauth_token_json=os.environ.get("GOOGLE_OAUTH_TOKEN_JSON", ""),
            notion_token=os.environ.get("NOTION_TOKEN", ""),
            notion_data_source_id=os.environ.get("NOTION_DATA_SOURCE_ID", ""),
            notion_version=os.environ.get("NOTION_VERSION", DEFAULT_NOTION_VERSION),
            github_token=os.environ.get("GITHUB_TOKEN", ""),
            github_repository=os.environ.get("GITHUB_REPOSITORY", ""),
            review_issue_title=os.environ.get("REVIEW_ISSUE_TITLE", REVIEW_ISSUE_TITLE),
        )

    def require_scan(self) -> None:
        missing = [
            name
            for name, value in {
                "GOOGLE_OAUTH_CLIENT_JSON": self.google_oauth_client_json,
                "GOOGLE_OAUTH_TOKEN_JSON": self.google_oauth_token_json,
                "NOTION_TOKEN": self.notion_token,
                "NOTION_DATA_SOURCE_ID": self.notion_data_source_id,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    def require_github(self) -> None:
        missing = [
            name
            for name, value in {
                "GITHUB_TOKEN": self.github_token,
                "GITHUB_REPOSITORY": self.github_repository,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required GitHub environment variables: {', '.join(missing)}")
