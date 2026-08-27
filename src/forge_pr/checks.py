from __future__ import annotations

import re

from .models import DeterministicCheck, ReviewFinding, Severity


SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
)


def deterministic_diff_checks(patch: str) -> tuple[list[DeterministicCheck], list[ReviewFinding]]:
    checks: list[DeterministicCheck] = []
    findings: list[ReviewFinding] = []

    has_conflict = "<<<<<<<" in patch or ">>>>>>>" in patch
    checks.append(
        DeterministicCheck(
            name="merge-conflict-markers",
            passed=not has_conflict,
            blocking=True,
            detail="No unresolved merge-conflict markers found."
            if not has_conflict
            else "Unresolved merge-conflict markers are present in the patch.",
        )
    )

    secret_match = SECRET_RE.search(patch)
    checks.append(
        DeterministicCheck(
            name="obvious-secret-pattern",
            passed=secret_match is None,
            blocking=True,
            detail="No obvious inline credential assignment detected."
            if secret_match is None
            else "Patch contains a credential-like inline assignment that requires review.",
        )
    )

    additions = sum(1 for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in patch.splitlines() if line.startswith("-") and not line.startswith("---"))
    checks.append(
        DeterministicCheck(
            name="patch-size",
            passed=(additions + deletions) <= 1200,
            blocking=False,
            detail=f"Patch changes {additions + deletions} lines ({additions} additions, {deletions} deletions).",
        )
    )

    if additions + deletions > 1200:
        findings.append(
            ReviewFinding(
                code="large-change",
                title="Large pull request",
                severity=Severity.warning,
                confidence=1.0,
                explanation="Large changes are harder to review and increase regression risk; consider splitting the PR.",
                deterministic=True,
            )
        )

    return checks, findings
