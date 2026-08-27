from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    info = "info"
    warning = "warning"
    high = "high"
    critical = "critical"


class GateDecision(StrEnum):
    pass_ = "pass"
    warn = "warn"
    block = "block"


class PullRequestInput(BaseModel):
    repository: str
    number: int = Field(ge=1)
    title: str
    body: str = ""
    base_sha: str
    head_sha: str
    changed_files: list[str]
    patch: str


class EvidenceRef(BaseModel):
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    symbol: str | None = None
    score: float = 0.0


class ReviewFinding(BaseModel):
    code: str
    title: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    deterministic: bool = False


class TestSuggestion(BaseModel):
    target: str
    rationale: str
    test_type: str = "unit"
    priority: Severity = Severity.warning


class GeneratedTest(BaseModel):
    target: str
    proposed_path: str
    framework: str = "pytest"
    content: str
    rationale: str


class TestExecution(BaseModel):
    command: list[str]
    passed: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = Field(ge=0.0)


class DeterministicCheck(BaseModel):
    name: str
    passed: bool
    blocking: bool = False
    detail: str


class AgentReviewOutput(BaseModel):
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str


class AgentTestOutput(BaseModel):
    suggestions: list[TestSuggestion] = Field(default_factory=list)
    generated_tests: list[GeneratedTest] = Field(default_factory=list)


class ReviewReport(BaseModel):
    repository: str
    pr_number: int
    decision: GateDecision
    summary: str
    findings: list[ReviewFinding]
    tests: list[TestSuggestion]
    generated_tests: list[GeneratedTest] = Field(default_factory=list)
    test_executions: list[TestExecution] = Field(default_factory=list)
    deterministic_checks: list[DeterministicCheck]
    changed_files: list[str]
    context_confidence: float = Field(ge=0.0, le=1.0)


class WorkflowState(BaseModel):
    pr: PullRequestInput
    repo_path: str
    context_pack: dict[str, Any] | None = None
    findings: list[ReviewFinding] = Field(default_factory=list)
    tests: list[TestSuggestion] = Field(default_factory=list)
    generated_tests: list[GeneratedTest] = Field(default_factory=list)
    test_executions: list[TestExecution] = Field(default_factory=list)
    deterministic_checks: list[DeterministicCheck] = Field(default_factory=list)
    report: ReviewReport | None = None
