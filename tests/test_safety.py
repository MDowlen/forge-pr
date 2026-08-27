from forge_pr.executor import TestExecutor
from forge_pr.models import GeneratedTest, ReviewReport, GateDecision
from forge_pr.publish import render_markdown


def test_generated_test_execution_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("FORGE_PR_EXECUTE_GENERATED_TESTS", raising=False)
    test = GeneratedTest(
        target="app.py",
        proposed_path="tests/test_generated.py",
        content="def test_ok():\n    assert True\n",
        rationale="coverage",
    )
    assert TestExecutor().run(str(tmp_path), [test]) == []


def test_markdown_separates_ai_and_deterministic_results():
    report = ReviewReport(
        repository="acme/app",
        pr_number=1,
        decision=GateDecision.pass_,
        summary="safe",
        findings=[],
        tests=[],
        deterministic_checks=[],
        changed_files=["app.py"],
        context_confidence=0.9,
    )
    text = render_markdown(report)
    assert "AI findings are advisory" in text
    assert "Decision" in text
