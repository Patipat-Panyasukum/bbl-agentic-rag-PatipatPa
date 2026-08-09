# Development

## Prerequisites

- Git
- Python with `venv` support
- Node.js 20.9 or newer with npm
- An OpenAI API key for retrieval evaluation and the agent workflow
- A LangSmith API key only when tracing is enabled

The current dependency set, including local Chroma, imports successfully in the
local Python 3.13.5 environment. `pip check` is part of verification because
Chroma and the LangGraph development server both depend on OpenTelemetry.

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

The retrieval tool has two deterministic modes. A normal personal question uses
the selected employee profile to filter candidates before vector ranking. When
the original question explicitly names a job-level policy audience (for example
`JL8`), the tool instead selects source policies whose metadata range covers
that level, answers the policy question, and marks each result as applying or
not applying to the selected profile. The typed level never replaces the
trusted employee ID, country, company, or employee type.

When changing a rule, update the policy text only when the source policy itself
changes. Update the sidecar when ingestion, search vocabulary, or demo employee
eligibility changes. `KNOWLEDGE_BASE_PATH` and `POLICY_METADATA_PATH` can point
to alternate files for testing.

`CHROMA_PATH` defaults to `data/chroma`. The directory is generated, local,
ignored by Git, and rebuildable from the two policy files. On the first search,
the application embeds and indexes the policy clauses. Later processes reuse
unchanged vectors; editing source text, retrieval terms, eligibility metadata,
the embedding model, or the chunking strategy causes affected generated rows to
be rebuilt automatically. No separate Chroma server is required.
Anonymized Chroma product telemetry is disabled by the application.

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
fails. Model, threshold, dataset, knowledge-base, employee database, Chroma
path, and Top-K values can be overridden through `--help` options.

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

Run the full-workflow evaluation, starting with one low-cost canary:

```powershell
python scripts/evaluate_agents.py --limit 1
python scripts/evaluate_agents.py
```

Regenerate the compiled graph image after changing nodes or edges:

```powershell
python scripts/export_graph_diagram.py
```

Validate and start the official LangGraph development server:

```powershell
langgraph validate
langgraph dev
```

To inspect a policy audience and its separate current-profile note:

```powershell
python scripts/run_cli.py `
  --employee-id E001 `
  --query "นโยบายสำหรับพนักงานระดับ JL8 เบิกค่ารักษาพยาบาลผู้ป่วยนอกได้เท่าไร" `
  --show-evidence
```

`langgraph dev` serves the local graph API at `http://127.0.0.1:2024` and opens
LangSmith Studio so reviewers can inspect the four sequential nodes. Use
`langgraph dev --no-browser` only when running a headless smoke test. Studio
requires a LangSmith sign-in, but local application tracing remains controlled
by the `LANGSMITH_TRACING` setting in `.env`.

## Run the demo UI

The browser application is a customized Agent Chat UI under `frontend/`. It
uses a local fictional profile selector; it is intentionally not production
authentication. The selected employee ID is sent as graph input and the Python
application resolves trusted context from SQLite before either LLM runs.

Keep `langgraph dev` running, then use a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Local defaults point to graph ID `benefitwise` at
`http://127.0.0.1:2024`; copy `frontend/.env.example` only when those public
browser settings need overriding. Never add `OPENAI_API_KEY` or
`LANGSMITH_API_KEY` to the frontend environment.

The header's **Chat history** link opens saved LangGraph threads for the chosen
fictional profile only. It is useful for reviewer navigation during a local
demo, but it is not a production audit or retention mechanism.

Run the headless layout/session smoke against already-running local servers:

```powershell
cd frontend
npm run ui:smoke
```

Run one real graph case and optionally regenerate all reviewer scenarios:

```powershell
$env:LIVE_UI_SMOKE = "1"
npm run ui:smoke

$env:CAPTURE_ALL_DEMO = "1"
npm run ui:smoke
```

The capture uses the installed Microsoft Edge through `playwright-core` and
writes reviewer screenshots under `docs/assets`. Live mode sends the natural
Thai OPD question through the graph, verifies the eligible OPD tool result and
grounded `14,250`-baht answer, verifies all four observable activity steps,
exercises evidence/activity collapse and tool visibility, checks that expanded
evidence does not overlap the composer on desktop or mobile, and captures both
views. It also verifies the JL8 policy-scope answer includes the OPD policy and
the separate E001/JL3 applicability note. Finally, it opens Chat history and
returns to the saved conversation by its real thread ID. It invokes the
configured embedding and chat models and therefore has API cost. The
deterministic Python and TypeScript checks remain free of model calls.

When `LANGSMITH_TRACING=true` and a valid key/project are configured, LangChain
and LangGraph calls emit traces for graph inspection. CLI, smoke, and evaluation
runs add source/case labels documented in
[docs/OBSERVABILITY.md](OBSERVABILITY.md). Use only fictional or approved data;
normal traces contain graph inputs and outputs.

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
