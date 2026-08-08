# Development

## Prerequisites

- Git
- Python with `venv` support
- An OpenAI-compatible API key only when an LLM-backed slice is reached
- A LangSmith API key only when tracing is enabled

The current dependency set imports successfully in the local Python 3.13.5
environment. Dependencies are intentionally unchanged in the workflow slice;
compatibility and version constraints will be reviewed when the first runtime
APIs are implemented.

## Windows PowerShell setup

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
Copy-Item .env.example .env
```

Populate `.env` locally and never commit it. Empty values in `.env.example`
document required variable names without exposing credentials.

On Windows systems using a legacy console code page, the LangGraph CLI can fail
while printing Unicode help text. Enable Python UTF-8 mode in that shell:

```powershell
$env:PYTHONUTF8 = "1"
langgraph --help
```

This is a console-output setting, not an application secret. `langgraph dev`
will become a supported project command only after graph code and its LangGraph
configuration exist.

Create or refresh the ignored local employee database:

```powershell
python scripts/seed_employees.py
```

The command is idempotent and seeds E001/JL3, E002/JL6, and E003/JL9. Tests use
temporary databases and never depend on this local file.

Run the retrieval evaluation with the real local embedding model:

```powershell
python scripts/evaluate_retrieval.py
```

The first run downloads `sentence-transformers/all-MiniLM-L6-v2`. The command
requires no OpenAI or LangSmith key. Model, threshold, dataset, knowledge-base,
database, and Top-K values can be overridden through `--help` options.

## Engineering loop

1. **Inspect:** read relevant code, tests, plans, and decisions first.
2. **Plan:** choose the smallest useful slice, likely files, behavior, and
   verification. Track multi-step work in `PLANS.md`.
3. **Implement:** keep business rules, retrieval, agents, and orchestration in
   separate modules; avoid unrelated refactors.
4. **Test:** run the narrowest relevant checks first, then the broader suite,
   including success and failure behavior.
5. **Review:** inspect the diff for duplication, complexity, broken imports,
   secret leakage, and accidental scope changes.
6. **Evaluate:** for AI/RAG changes, measure behavior and groundedness in
   addition to Python correctness.
7. **Document:** update affected architecture, development, testing, decisions,
   plan, and reviewer guidance.
8. **Commit-ready:** summarize changes, exact commands/results, limitations,
   and a focused commit-message suggestion.

## Verification commands

Use commands appropriate to the slice; do not claim commands that were not run.

```powershell
# Narrow tests (once they exist)
pytest tests/unit -q

# Full regression suite
pytest -q

# Whitespace and patch sanity
git diff --check

# Review changed files and ignore behavior
git status --short --ignored
git diff --stat
git diff
```

If pytest cannot access its default per-user temp directory on Windows, point
it at the already-ignored project cache:

```powershell
pytest -q --basetemp=.pytest_cache\basetemp
```

Evaluation commands and datasets will be added with semantic retrieval. Record
measured Hit@K/MRR and smoke-test outcomes in the relevant plan or report rather
than embedding aspirational results in the README.

## Git workflow

- Start work from an up-to-date `main` branch.
- Use focused branches such as `feat/core-rag`, `feat/langgraph-agents`,
  `feat/evaluation-observability`, and `feat/demo-ui`.
- Keep commits meaningful and reviewable; do not mix unrelated cleanup with a
  feature slice.
- Before committing, check that `.env`, `.venv/`, generated databases, local
  agent configuration, caches, and credentials are not tracked.

## Current verification state

The deterministic unit and retrieval tests require no network access or API
keys because they inject a controlled embedding provider. The separate
evaluation command uses the real sentence-transformer model. Actual commands
and results are recorded in [PLANS.md](../PLANS.md) and
[eval/RESULTS.md](../eval/RESULTS.md).
