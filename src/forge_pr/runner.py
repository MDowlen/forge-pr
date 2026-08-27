from __future__ import annotations

from pathlib import Path

from .github import GitHubClient
from .graph import build_graph
from .models import PullRequestInput, ReviewReport, WorkflowState


def run_review(pr: PullRequestInput, repo_path: Path) -> ReviewReport:
    state = WorkflowState(pr=pr, repo_path=str(repo_path.resolve()))
    result = build_graph().invoke(state)
    report = result.get("report") if isinstance(result, dict) else result.report
    if report is None:
        raise RuntimeError("ForgePR workflow completed without a review report")
    return ReviewReport.model_validate(report)


def run_github_review(repository: str, number: int, repo_path: Path) -> ReviewReport:
    pr = GitHubClient().pull_request(repository, number)
    return run_review(pr, repo_path)
