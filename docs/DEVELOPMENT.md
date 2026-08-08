# Development

## Prerequisites

- Git
- Python with `venv` support
- An OpenAI API key for retrieval evaluation and the agent workflow
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

Policy content and retrieval configuration are intentionally separate:

- `knowledge_base.txt` contains only sanitized policy prose and numbered clauses.
- `policy_metadata.json` contains the derived section mapping, retrieval terms,
  and deterministic eligibility fields.

When changing a rule, update the policy text only when the source policy itself
changes. Update the sidecar when ingestion, search vocabulary, or demo employee
eligibility changes. `KNOWLEDGE_BASE_PATH` and `POLICY_METADATA_PATH` can point
to alternate files for testing.

On Windows systems using a legacy console code page, the LangGraph CLI can fail
while printing Unicode help text. Enable Python UTF-8 mode in that shell:

```powershell
$env:PYTHONUTF8 = "1"
langgraph --help
```

This is a console-output setting, not an application secret.

Create or refresh the ignored local employee database:

```powershell
python scripts/seed_employees.py
```

The command is idempotent and seeds E001/JL3 General, E002/JL6 General, and
E003/JL1 Operations under the fictional `DEMO` company. Tests use temporary
databases and never depend on this local file.

Run the retrieval evaluation with the real OpenAI embedding model:

```powershell
python scripts/evaluate_retrieval.py
```

The command uses `text-embedding-3-small` and requires `OPENAI_API_KEY` in the
ignored `.env`. It returns a non-zero exit code if any committed retrieval case
fails. Model, threshold, dataset, knowledge-base, database, and Top-K values can
be overridden through `--help` options.

## Run the agent workflow

Set `OPENAI_API_KEY` in `.env`. Defaults and optional OpenAI-compatible endpoint
settings are documented in `.env.example`. The default model is
`gpt-5.6-luna` with the Responses API, low reasoning effort, and low verbosity.
It is shared by the narrowly scoped Data Retriever and grounded Report
Generator agents; all settings remain configurable without code changes.

Run one query:

```powershell
python scripts/run_cli.py `
  --employee-id E002 `
  --query "How much can I claim for outpatient medical expenses?" `
  --show-evidence
```

Run API-backed smoke cases from `examples/demo_queries.json`:

```powershell
python scripts/run_smoke_queries.py --limit 1
python scripts/run_smoke_queries.py
```

`--limit` controls API cost during development. The full set checks General and
Operations OPD limits, a Thai IPD question, the social-security-first rule, and
an unsupported question.

Validate and start the official LangGraph development server:

```powershell
langgraph validate
langgraph dev
```

When `LANGSMITH_TRACING=true` and a valid key/project are configured, LangChain
and LangGraph calls emit traces for graph inspection.

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

Record measured Hit@K/MRR and smoke-test outcomes in the relevant plan or report
rather than substituting aspirational results.

## Git workflow

- Start work from an up-to-date `main` branch.
- Use focused branches such as `feat/core-rag`, `feat/langgraph-agents`,
  `feat/evaluation-observability`, and `feat/demo-ui`.
- Keep commits meaningful and reviewable; do not mix unrelated cleanup with a
  feature slice.
- Before committing, check that `.env`, `.venv/`, generated databases, local
  agent configuration, caches, and credentials are not tracked.

## Current verification state

The automated unit/integration suite requires no network access or API keys
because it injects controlled embedding and chat models. The separate retrieval
evaluation and CLI/smoke commands use real models. Actual commands and results
are recorded in [PLANS.md](../PLANS.md) and [eval/RESULTS.md](../eval/RESULTS.md).
