from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .models import GeneratedTest, TestExecution


class TestExecutor:
    """Run generated pytest files in an ephemeral copy of the repository.

    This is filesystem isolation, not a security sandbox. Execution is disabled by
    default because model-generated code must be treated as untrusted. Production
    CI should run this process inside a hardened container/runner with restricted
    credentials and network access.
    """

    def __init__(self, enabled: bool | None = None, timeout_seconds: int = 90) -> None:
        if enabled is None:
            enabled = os.getenv("FORGE_PR_EXECUTE_GENERATED_TESTS", "0") == "1"
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    def run(self, repo_path: str, generated_tests: list[GeneratedTest]) -> list[TestExecution]:
        if not self.enabled or not generated_tests:
            return []

        root = Path(repo_path).resolve()
        with tempfile.TemporaryDirectory(prefix="forge-pr-") as temp_dir:
            workspace = Path(temp_dir) / "repo"
            shutil.copytree(
                root,
                workspace,
                ignore=shutil.ignore_patterns(
                    ".git", ".venv", "__pycache__", ".pytest_cache", ".forge-context"
                ),
            )
            paths: list[str] = []
            for test in generated_tests:
                relative = Path(test.proposed_path)
                target = (workspace / relative).resolve()
                if workspace not in target.parents:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(test.content, encoding="utf-8")
                paths.append(relative.as_posix())

            if not paths:
                return []

            command = [sys.executable, "-m", "pytest", *paths, "-q"]
            started = time.monotonic()
            try:
                result = subprocess.run(
                    command,
                    cwd=workspace,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    env={**os.environ, "PYTHONPATH": str(workspace)},
                )
                duration = time.monotonic() - started
                return [
                    TestExecution(
                        command=command,
                        passed=result.returncode == 0,
                        exit_code=result.returncode,
                        stdout=result.stdout[-12000:],
                        stderr=result.stderr[-12000:],
                        duration_seconds=duration,
                    )
                ]
            except subprocess.TimeoutExpired as exc:
                duration = time.monotonic() - started
                return [
                    TestExecution(
                        command=command,
                        passed=False,
                        exit_code=124,
                        stdout=(exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
                        stderr="Generated test execution timed out.",
                        duration_seconds=duration,
                    )
                ]
