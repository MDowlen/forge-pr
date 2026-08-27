from __future__ import annotations

from pydantic import BaseModel, Field

from .models import GateDecision, ReviewReport


class ReviewEvalCase(BaseModel):
    name: str
    expected_decision: GateDecision
    expected_finding_codes: list[str] = Field(default_factory=list)
    forbidden_finding_codes: list[str] = Field(default_factory=list)


class ReviewEvalResult(BaseModel):
    name: str
    decision_correct: bool
    finding_recall: float = Field(ge=0.0, le=1.0)
    forbidden_false_positives: int = Field(ge=0)


class ReviewEvalReport(BaseModel):
    cases: int
    decision_accuracy: float = Field(ge=0.0, le=1.0)
    mean_finding_recall: float = Field(ge=0.0, le=1.0)
    false_positive_count: int = Field(ge=0)
    results: list[ReviewEvalResult]


def score_review(report: ReviewReport, case: ReviewEvalCase) -> ReviewEvalResult:
    codes = {finding.code for finding in report.findings}
    expected = set(case.expected_finding_codes)
    recalled = len(codes & expected)
    recall = recalled / len(expected) if expected else 1.0
    forbidden = len(codes & set(case.forbidden_finding_codes))
    return ReviewEvalResult(
        name=case.name,
        decision_correct=report.decision == case.expected_decision,
        finding_recall=recall,
        forbidden_false_positives=forbidden,
    )


def aggregate_results(results: list[ReviewEvalResult]) -> ReviewEvalReport:
    count = len(results)
    return ReviewEvalReport(
        cases=count,
        decision_accuracy=(sum(item.decision_correct for item in results) / count) if count else 0.0,
        mean_finding_recall=(sum(item.finding_recall for item in results) / count) if count else 0.0,
        false_positive_count=sum(item.forbidden_false_positives for item in results),
        results=results,
    )
