from __future__ import annotations

from .checks import deterministic_diff_checks
from .context import ForgeContextAdapter
from .models import (
    GateDecision,
    ReviewFinding,
    ReviewReport,
    Severity,
    TestSuggestion,
    WorkflowState,
)


def context_node(state: WorkflowState) -> dict:
    question = (
        "Review this pull request using repository code, architecture decisions, dependency impact, "
        "and testing context. Identify what changed and what could regress."
    )
    pack = ForgeContextAdapter().pack(
        state.repo_path,
        question,
        state.pr.changed_files,
    )
    return {"context_pack": pack}


def deterministic_node(state: WorkflowState) -> dict:
    checks, findings = deterministic_diff_checks(state.pr.patch)
    return {
        "deterministic_checks": checks,
        "findings": [*state.findings, *findings],
    }


def quality_node(state: WorkflowState) -> dict:
    """Phase-1 grounded heuristic reviewer; replaced/augmented by LLM review in Phase 2."""
    findings = list(state.findings)
    pack = state.context_pack or {}
    answer = pack.get("answer", {})
    confidence = float(answer.get("confidence", 0.0) or 0.0)
    citations = answer.get("citations", [])
    if confidence < 0.2 or not citations:
        findings.append(
            ReviewFinding(
                code="low-context-confidence",
                title="Repository context is weak",
                severity=Severity.warning,
                confidence=1.0,
                explanation=(
                    "ForgeContext did not retrieve strong evidence for this change. "
                    "Human review should not rely on automated architectural conclusions."
                ),
                deterministic=False,
            )
        )
    return {"findings": findings}


def test_plan_node(state: WorkflowState) -> dict:
    tests: list[TestSuggestion] = []
    for path in state.pr.changed_files[:12]:
        if path.startswith("tests/") or "/test" in path or path.startswith("test_"):
            continue
        tests.append(
            TestSuggestion(
                target=path,
                rationale="Changed production code should have behavior/regression coverage.",
                test_type="unit/integration",
                priority=Severity.warning,
            )
        )
    return {"tests": tests}


def gate_node(state: WorkflowState) -> dict:
    blocking_failures = [
        check for check in state.deterministic_checks if check.blocking and not check.passed
    ]
    high_findings = [
        finding
        for finding in state.findings
        if finding.severity in {Severity.high, Severity.critical}
    ]
    warnings = [finding for finding in state.findings if finding.severity == Severity.warning]

    if blocking_failures:
        decision = GateDecision.block
        summary = "Blocked by deterministic safety checks."
    elif high_findings:
        decision = GateDecision.warn
        summary = "No deterministic blocker, but high-severity review findings require human review."
    elif warnings:
        decision = GateDecision.warn
        summary = "Deterministic checks passed; non-blocking review warnings remain."
    else:
        decision = GateDecision.pass_
        summary = "Deterministic checks passed and no material findings were produced."

    pack = state.context_pack or {}
    confidence = float((pack.get("answer") or {}).get("confidence", 0.0) or 0.0)
    report = ReviewReport(
        repository=state.pr.repository,
        pr_number=state.pr.number,
        decision=decision,
        summary=summary,
        findings=state.findings,
        tests=state.tests,
        deterministic_checks=state.deterministic_checks,
        changed_files=state.pr.changed_files,
        context_confidence=confidence,
    )
    return {"report": report}
