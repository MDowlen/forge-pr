from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .models import PullRequestInput
from .runner import run_github_review, run_review

app = typer.Typer(help="ForgePR grounded pull-request validator")
console = Console()


def _render(report) -> None:
    console.print(f"[bold]Decision:[/bold] {report.decision.value}")
    console.print(report.summary)
    table = Table(title="Deterministic checks")
    table.add_column("Check")
    table.add_column("Pass")
    table.add_column("Blocking")
    table.add_column("Detail")
    for check in report.deterministic_checks:
        table.add_row(check.name, str(check.passed), str(check.blocking), check.detail)
    console.print(table)
    if report.findings:
        findings = Table(title="Review findings")
        findings.add_column("Severity")
        findings.add_column("Finding")
        findings.add_column("Confidence")
        for item in report.findings:
            findings.add_row(item.severity.value, item.title, f"{item.confidence:.2f}")
        console.print(findings)


@app.command("review")
def review(
    repository: str = typer.Option(..., "--repo", help="GitHub owner/repository"),
    pr_number: int = typer.Option(..., "--pr", min=1),
    repo_path: Path = typer.Option(Path("."), "--path", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Fetch and review a GitHub pull request against a local repository checkout."""
    report = run_github_review(repository, pr_number, repo_path)
    if json_output:
        console.print_json(json.dumps(report.model_dump(mode="json")))
    else:
        _render(report)
    if report.decision.value == "block":
        raise typer.Exit(code=2)


@app.command("fixture")
def fixture(
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    repo_path: Path = typer.Option(Path("."), "--path", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Review a saved PullRequestInput JSON fixture without GitHub network access."""
    payload = json.loads(input_file.read_text(encoding="utf-8"))
    report = run_review(PullRequestInput.model_validate(payload), repo_path)
    if json_output:
        console.print_json(json.dumps(report.model_dump(mode="json")))
    else:
        _render(report)
    if report.decision.value == "block":
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
