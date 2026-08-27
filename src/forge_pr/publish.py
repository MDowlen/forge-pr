from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .models import ReviewReport


def render_markdown(report: ReviewReport) -> str:
    lines = [
        "## ForgePR review",
        "",
        f"**Decision:** `{report.decision.value}`",
        "",
        report.summary,
        "",
        f"Context confidence: `{report.context_confidence:.2f}`",
        "",
        "### Deterministic checks",
    ]
    for check in report.deterministic_checks:
        icon = "✅" if check.passed else "❌"
        lines.append(f"- {icon} **{check.name}** — {check.detail}")
    if report.findings:
        lines.extend(["", "### Findings"])
        for finding in report.findings:
            lines.append(
                f"- **{finding.severity.value.upper()} · {finding.title}** "
                f"(confidence {finding.confidence:.2f}) — {finding.explanation}"
            )
    if report.tests:
        lines.extend(["", "### Suggested coverage"])
        for test in report.tests:
            lines.append(f"- `{test.target}` — {test.rationale}")
    if report.test_executions:
        lines.extend(["", "### Generated-test execution"])
        for execution in report.test_executions:
            icon = "✅" if execution.passed else "❌"
            lines.append(
                f"- {icon} exit `{execution.exit_code}` in {execution.duration_seconds:.2f}s"
            )
    lines.extend(
        [
            "",
            "> AI findings are advisory. Deterministic checks and executed tests are reported separately.",
        ]
    )
    return "\n".join(lines)


class GitHubPublisher:
    def __init__(self, token: str | None = None, api_url: str = "https://api.github.com") -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = api_url.rstrip("/")

    def publish_comment(self, report: ReviewReport) -> dict:
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is required to publish a ForgePR review")
        owner, repo = report.repository.split("/", 1)
        payload = json.dumps({"body": render_markdown(report)}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_url}/repos/{owner}/{repo}/issues/{report.pr_number}/comments",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "forge-pr",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub publish failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub publish failed: {exc.reason}") from exc
