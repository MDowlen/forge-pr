from __future__ import annotations

from pathlib import Path

from forge_context import ContextEngine
from forge_context.config import Settings
from forge_context.factory import make_backend, make_embedder


class ForgeContextAdapter:
    """Build ForgeContext context packs for PR review workflows."""

    def __init__(self) -> None:
        settings = Settings.from_env()
        embedder = make_embedder(settings)
        backend = make_backend(settings, dimensions=embedder.dimensions)
        self.engine = ContextEngine(backend, embedder)

    def pack(self, repo_path: str, question: str, changed_files: list[str]) -> dict:
        pack = self.engine.context_pack(
            Path(repo_path),
            question,
            changed_files=changed_files,
            limit=8,
            decision_limit=12,
            impact_depth=4,
        )
        return pack.model_dump(mode="json")
