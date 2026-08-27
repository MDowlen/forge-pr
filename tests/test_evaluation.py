from forge_pr.evaluation import ReviewEvalCase, aggregate_results, score_review
from forge_pr.models import GateDecision, ReviewFinding, ReviewReport, Severity


def _report(decision: GateDecision, codes: list[str]) -> ReviewReport:
    return ReviewReport(
        repository="acme/app",
        pr_number=1,
        decision=decision,
        summary="test",
        findings=[
            ReviewFinding(
                code=code,
                title=code,
                severity=Severity.warning,
                confidence=1.0,
                explanation="test",
            )
            for code in codes
        ],
        tests=[],
        deterministic_checks=[],
        changed_files=["app.py"],
        context_confidence=0.8,
    )


def test_review_evaluation_tracks_recall_and_false_positives():
    case = ReviewEvalCase(
        name="regression",
        expected_decision=GateDecision.warn,
        expected_finding_codes=["missing-test", "null-risk"],
        forbidden_finding_codes=["fake-security"],
    )
    result = score_review(
        _report(GateDecision.warn, ["missing-test", "fake-security"]),
        case,
    )
    report = aggregate_results([result])
    assert report.decision_accuracy == 1.0
    assert report.mean_finding_recall == 0.5
    assert report.false_positive_count == 1
