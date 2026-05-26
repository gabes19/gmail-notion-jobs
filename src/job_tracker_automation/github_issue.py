from __future__ import annotations

import requests


class GitHubIssueClient:
    def __init__(self, token: str, repository: str) -> None:
        if "/" not in repository:
            raise ValueError("GITHUB_REPOSITORY must be in owner/name form.")
        self.repository = repository
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def upsert_issue(self, title: str, body: str) -> str:
        issue = self._find_open_issue(title)
        if issue:
            response = self.session.patch(
                f"https://api.github.com/repos/{self.repository}/issues/{issue['number']}",
                json={"body": body},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["html_url"]
        response = self.session.post(
            f"https://api.github.com/repos/{self.repository}/issues",
            json={"title": title, "body": body, "labels": ["automation", "job-search"]},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["html_url"]

    def _find_open_issue(self, title: str) -> dict | None:
        response = self.session.get(
            f"https://api.github.com/repos/{self.repository}/issues",
            params={"state": "open", "per_page": 100},
            timeout=30,
        )
        response.raise_for_status()
        for issue in response.json():
            if "pull_request" not in issue and issue.get("title") == title:
                return issue
        return None
