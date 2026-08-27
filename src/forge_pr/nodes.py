from __future__ import annotations

from .ai import OpenAIReviewClient
from .checks import deterministic_diff_checks
from .context import ForgeContextAdapter
from .models import (
    EvidenceRef,
    GateDecision,
    GeneratedTest,
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


def _valid_evidence(pack: dict, evidence: list[EvidenceRef]) -> list[EvidenceRef]:
    citations = (pack.get("answer") or {}).get("citations", [])
    valid: list[EvidenceRef] = []
    for item in evidence:
        for citation in citations:
            if item.path != citation.get("path"):
                continue
            if item.start_line < int(citation.get("start_line", 1)):
                continue
            if item.end_line > int(citation.get("end_line", item.end_line)):
                continue
            valid.append(item)
            break
    return valid


def _agent_payload(state: WorkflowState) -> dict:
    return {
        "pull_request": {
            "repository": state.pr.repository,
            "number": state.pr.number,
            "title": state.pr.title,
            "body": state.pr.body[:5000],
            "changed_files": state.pr.changed_files,
            "patch": state.pr.patch[:60000],
        },
        "context_pack": state.context_pack or {},
    }


def quality_node(state: WorkflowState) -> dict:
    findings = list(state.findings)
    pack = state.context_pack or {}
    answer = pack.get("answer", {})
    confidence = float(answer.get("confidence", 0.0) or 0.0)
    citations = answer.get("citations", [])
    client = OpenAIReviewClient()

    if client.enabled:
        output = client.review(_agent_payload(state))
        for finding in output.findings:
            finding.evidence = _valid_evidence(pack, finding.evidence)
            if not finding.evidence:
                finding.confidence = min(finding.confidence, 0.5)
            findings.append(finding)
    elif confidence < 0.2 or not citations:
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


def _fallback_test_plan(state: WorkflowState) -> list[TestSuggestion]:
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
    return tests


def _safe_generated_tests(items: list[GeneratedTest]) -> list[GeneratedTest]:
    safe: list[GeneratedTest] = []
    for item in items:
        path = item.proposed_path.replace("\\", "/")
        if not path.startswith("tests/"):
            continue
        if ".." in path.split("/"):
            continue
        if not path.endswith(".py"):
            continue
        if len(item.content) > 30000:
            continue
        safe.append(item)
    return safe


def test_plan_node(state: WorkflowState) -> dict:
    client = OpenAIReviewClient()
    if client.enabled:
        output = client.generate_tests(_agent_payload(state))
        return {
            "tests": output.suggestions,
            "generated_tests": _safe_generated_tests(output.generated_tests),
        }
    return {"tests": _fallback_test_plan(state), "generated_tests": []}


def gate_node(state: WorkflowState) -> dict:
    blocking_failures = [
        check for check in state.deterministic_checks if check.blocking and not check.passed
    ]
    failed_generated_tests = [execution for execution in state.test_executions if not execution.passed]
    high_findings = [
        finding
        for finding in state.findings
        if finding.severity in {Severity.high, Severity.critical}
    ]
    warnings = [finding for finding in state.findings if finding.severity == Severity.warning]

    if blocking_failures or failed_generated_tests:
        decision = GateDecision.block
        summary = "Blocked by deterministic safety or test-execution failures."
    elif high_findings:
        decision = GateDecision.warn
        summary = "No deterministic blocker, but high-severity AI findings require human review."
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
        generated_tests=state.generated_tests,
        test_executions=state.test_executions,
        deterministic_checks=state.deterministic_checks,
        changed_files=state.pr.changed_files,
        context_confidence=confidence,
    )
    return {"report": report}
