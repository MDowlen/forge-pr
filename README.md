# ForgePR

**RAG-grounded pull-request validation and CI quality gates.**

ForgePR is a LangGraph review system built on ForgeContext. It turns a GitHub pull-request diff into a typed review state, retrieves repository evidence, runs specialized quality/test agents, executes deterministic safety checks, and produces a structured merge recommendation.

## Design rule

> **AI may advise. Deterministic checks enforce.**

Model findings never silently become facts. ForgePR keeps deterministic checks and executed-test results separate from AI judgments, validates model evidence against ForgeContext citations, and caps confidence when an AI finding cannot be grounded.

## Capabilities

- GitHub PR metadata, changed-file, and unified-diff ingestion
- ForgeContext `ContextEngine` + structured `ContextPack`
- LangGraph state machine
- Pydantic contracts for every workflow boundary
- deterministic merge-conflict, obvious-secret, and patch-size checks
- OpenAI Responses API quality/safety agent using JSON-schema structured output
- model-backed test suggestions and pytest generation
- citation validation against ForgeContext evidence
- generated-test path/content validation
- generated-test execution in an ephemeral repository copy
- deterministic gate that can block on safety/test failures
- GitHub PR comment publisher
- review evaluation metrics: decision accuracy, finding recall, false-positive count
- local fixture mode for reproducible evaluation
- Python 3.11–3.13 CI matrix

## Workflow

```text
GitHub Pull Request
        |
        v
PR Diff Ingestion
        |
        v
ForgeContext ContextPack
(code + ADRs + history + impact)
        |
        v
LangGraph
  context
     |
  deterministic checks
     |
  quality/safety agent
     |
  test-generation agent
     |
  optional generated-test execution
     |
  deterministic decision gate
        |
        v
Structured ReviewReport
        |
        +--> terminal / JSON
        +--> GitHub PR comment
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

ForgePR directly depends on the public `MDowlen/forge-context` package source.

## Prepare repository context

```bash
dev-ai context sync .
```

## Review a GitHub pull request

```bash
export GITHUB_TOKEN=...
export OPENAI_API_KEY=...
export FORGE_PR_MODEL=gpt-5.4-mini

forge-pr review \
  --repo owner/repository \
  --pr 123 \
  --path .
```

Add `--json` for a machine-readable `ReviewReport` or `--publish` to post a PR comment.

## Generated tests

Generated code is treated as untrusted and **is not executed by default**. To opt in:

```bash
forge-pr review \
  --repo owner/repository \
  --pr 123 \
  --path . \
  --execute-generated-tests
```

The current executor writes generated tests into an ephemeral copy of the repository and runs only Python `pytest` against those generated paths with a timeout. This is filesystem isolation, **not a security sandbox**. Production CI should place this step in a hardened disposable runner/container with restricted credentials and network access.

## Offline / fixture mode

```bash
forge-pr fixture fixtures/pr.json --path . --json
```

Without `OPENAI_API_KEY`, the workflow remains functional using deterministic checks, ForgeContext retrieval, low-context safeguards, and deterministic test suggestions. This keeps CI and evaluation reproducible without paid model calls.

## Evaluation

ForgePR can score labeled review outputs on:

- decision accuracy
- expected finding recall
- forbidden/false-positive finding count

ForgeContext separately measures retrieval quality (Hit@K, MRR, citation integrity), which lets the project diagnose whether a bad review came from retrieval or agent reasoning.

## GitHub Actions

See `examples/forge-pr.yml` for a pull-request workflow that checks out the repo, builds ForgeContext, runs ForgePR, and optionally publishes the review.

## Development

```bash
ruff check src tests
pytest -q
```

## Security boundaries

- API keys are read from environment variables and never written to review state.
- AI evidence is checked against retrieved source citations.
- generated test paths must remain inside `tests/` and cannot use path traversal.
- generated tests are execution-disabled by default.
- deterministic blockers override model opinions.
- publishing requires an explicit CLI flag.

## Technology

Python · LangGraph · Pydantic · ForgeContext · Tree-sitter/RAG · OpenAI Responses API · Pytest · GitHub Actions

## License

MIT © 2026 Mareza Dowlen
