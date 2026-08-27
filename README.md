# ForgePR

**RAG-grounded pull-request validation and CI quality gates.**

ForgePR is the flagship review workflow built on top of ForgeContext. It turns a pull-request diff into a typed review state, retrieves repository evidence, separates deterministic CI facts from model judgments, and produces a structured merge recommendation.

## Phase 1

- GitHub pull-request metadata and patch ingestion
- ForgeContext `ContextEngine` adapter
- Pydantic review state and result contracts
- LangGraph orchestration
- deterministic diff-risk checks
- test-plan generation contract
- deterministic merge gate
- CLI for local/CI execution
- pytest + Ruff + GitHub Actions

## Core rule

> AI may advise. Deterministic checks enforce.

## Roadmap

Phase 2 adds model-backed quality/safety review and test generation with structured outputs. Phase 3 adds isolated test execution, GitHub review publishing, evaluation, and hardened CI gating.
