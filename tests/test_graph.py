from pathlib import Path

from forge_pr.graph import build_graph
from forge_pr.models import GateDecision, PullRequestInput, WorkflowState
import forge_pr.nodes as nodes


class FakeContextAdapter:
    def pack(self, repo_path: str, question: str, changed_files: list[str]) -> dict:
        return {
            "question": question,
            "answer": {
                "confidence": 0.91,
                "citations": [
                    {
                        "path": "src/app.py",
                        "start_line": 1,
                        "end_line": 10,
                        "symbol": "handler",
                        "score": 0.91,
                    }
                ],
            },
            "impact": {"changed_files": changed_files},
            "decisions": [],
        }


def test_graph_produces_pass_report(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(nodes, "ForgeContextAdapter", FakeContextAdapter)
    pr = PullRequestInput(
        repository="acme/app",
        number=7,
        title="Small safe change",
        base_sha="a" * 40,
        head_sha="b" * 40,
        changed_files=["src/app.py"],
        patch="diff --git a/src/app.py b/src/app.py\n+print('hello')\n",
    )
    result = build_graph().invoke(WorkflowState(pr=pr, repo_path=str(tmp_path)))
    report = result["report"]
    assert report.decision == GateDecision.pass_
    assert report.context_confidence == 0.91
    assert report.tests[0].target == "src/app.py"


def test_graph_blocks_deterministic_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(nodes, "ForgeContextAdapter", FakeContextAdapter)
    pr = PullRequestInput(
        repository="acme/app",
        number=8,
        title="Broken change",
        base_sha="a" * 40,
        head_sha="b" * 40,
        changed_files=["src/app.py"],
        patch="+<<<<<<< HEAD\n+print('a')\n+>>>>>>> branch\n",
    )
    result = build_graph().invoke(WorkflowState(pr=pr, repo_path=str(tmp_path)))
    assert result["report"].decision == GateDecision.block
