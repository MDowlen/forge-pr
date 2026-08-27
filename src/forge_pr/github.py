from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .models import PullRequestInput


class GitHubClient:
    """Minimal GitHub REST reader for pull-request metadata and patches."""

    def __init__(self, token: str | None = None, api_url: str = "https://api.github.com") -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = api_url.rstrip("/")

    def _request(self, path: str, accept: str = "application/vnd.github+json") -> bytes:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "forge-pr",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"{self.api_url}{path}", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub request failed: {exc.reason}") from exc

    def pull_request(self, repository: str, number: int) -> PullRequestInput:
        owner, repo = repository.split("/", 1)
        base = f"/repos/{owner}/{repo}"
        pr = json.loads(self._request(f"{base}/pulls/{number}").decode("utf-8"))
        files = json.loads(self._request(f"{base}/pulls/{number}/files?per_page=100").decode("utf-8"))
        patch = self._request(
            f"{base}/pulls/{number}", accept="application/vnd.github.v3.diff"
        ).decode("utf-8", errors="replace")
        return PullRequestInput(
            repository=repository,
            number=number,
            title=pr.get("title", ""),
            body=pr.get("body") or "",
            base_sha=pr["base"]["sha"],
            head_sha=pr["head"]["sha"],
            changed_files=[item["filename"] for item in files],
            patch=patch,
        )
