# Implementation Plan

## Current state

- Branch: `feat/core-rag`, based on the bootstrap commit on `main`.
- Tracked project content before this slice: dependency/environment files and
  an empty README.
- Implemented runtime layers: deterministic employee context and core RAG.
- Active branch: `feat/core-rag`, implementation complete and verified.

## Active slice: workflow baseline

Status: **complete (2026-08-08)**

- [x] Add concise coding-agent guidance.
- [x] Document the planned architecture and trusted data boundaries.
- [x] Document local development, testing, and technical decisions.
- [x] Add a truthful reviewer-facing README introduction.
- [x] Ignore machine-local `.codex/` configuration.
- [x] Verify document links, ignore rules, whitespace, imports, and test state.
- [x] Review the complete diff and record the result below.

### Verification record

- Markdown link/whitespace check: all seven Markdown files passed; all local
  link targets exist and every file ends with a newline.
- `git diff --check`: passed.
- `git check-ignore`: `.env`, `.venv/`, `.codex/`, generated databases,
  LangGraph state, and generated frontend paths are ignored.
- Core dependency import check: passed under Python 3.13.5.
- `python -m pytest --collect-only -q`: exited with code 5 because no tests are
  present. This is recorded as the current state, not a passing test suite.
- Diff review: changes are limited to the requested workflow documentation and
  ignore rule; no credentials, runtime code, or unsupported feature claims were
  introduced.

## Active slice: deterministic employee context

Status: **complete (2026-08-08)**

Create the Python package/test structure and implement only the trusted
employee-context boundary:

- [x] Define a small employee record with employee ID, job level, country, company,
  and employee type.
- [x] Seed fictional E001/JL3, E002/JL6, and E003/JL9 records in local SQLite.
- [x] Provide deterministic lookup by employee ID; unknown IDs return an explicit
  not-found result and never fall through to an LLM.
- [x] Unit-test all three known profiles, unknown IDs, and repeatable database
  initialization.
- [x] Keep retrieval, embeddings, tools, agents, and LangGraph out of this slice.
- [x] Run narrow and full tests, inspect the diff, and record actual results.

### Verification record

- Initial `python -m pytest tests\\unit -q`: nine setup errors because pytest
  could not access the default Windows user temp directory; no test assertions
  ran in this attempt.
- `python -m pytest tests\\unit -q --basetemp=.pytest_cache\\basetemp`: nine
  tests passed in 0.13 seconds.
- `python -m pytest -q --basetemp=.pytest_cache\\full-suite`: nine tests passed
  in 0.13 seconds.
- `python -m compileall -q src scripts tests`: passed.
- Editable package install, employee seed command, and direct lookups for E001,
  E002, and E003: passed with the expected JL3, JL6, and JL9 contexts.
- Repeated default seeding retained exactly three employee rows; `pip check`
  reported no broken requirements.
- `git diff --check`, changed-file whitespace/newline checks, Markdown link
  checks, secret scan, and scope scan: passed. Generated database, cache, and
  editable-install metadata remain ignored.

## Active branch outcome: core RAG

Status: **complete (2026-08-08)**

- [x] Author 12 local policies with explicit eligibility metadata.
- [x] Parse strict policy blocks and reject unsafe malformed input.
- [x] Filter country, company, employee type, and job level before embeddings.
- [x] Implement sentence embeddings, cosine similarity, thresholding, and Top-K.
- [x] Expose an employee-bound custom LangChain retrieval tool.
- [x] Add deterministic parser, eligibility, retrieval, tool, and metric tests.
- [x] Add and execute a 13-case real-model retrieval evaluation.
- [x] Complete full regression, diff review, and branch documentation review.

### Evaluation record

- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Configuration: cosine similarity, minimum score `0.25`, Top-3.
- Dataset: 11 positive and two expected-no-evidence cases.
- Result: Hit@1 `1.000`, Hit@3 `1.000`, MRR `1.000`, no-evidence accuracy
  `1.000`; all 13 cases passed.

### Verification record

- `python -m pytest -q --basetemp=.pytest_cache\\core-final`: 46 tests passed
  in 0.40 seconds.
- `python scripts/evaluate_retrieval.py`: all 13 cases passed again with the
  recorded metrics.
- Real-model LangChain tool smoke test for E002/JL6 returned
  `MED-OPD-JL5-7`, THB 40,000, at similarity `0.4401`.
- `python -m compileall -q src scripts tests` and `pip check`: passed.
- JSON parsing, policy/evaluation counts, Markdown links, whitespace/newlines,
  `git diff --check`, ignored-artifact checks, TODO/secret scan, and scope review:
  passed.

## Next branch: agent workflow

After this branch is reviewed and merged, create `feat/langgraph-agents` from
the updated `main`. Implement the Data Retriever Agent, Report Generator Agent,
explicit graph state, sequential LangGraph orchestration, and CLI smoke queries.

## Incremental roadmap

1. **Employee context (complete)** - package structure, SQLite seed, deterministic lookup,
   and unit tests.
2. **Policy foundation (complete)** - author `knowledge_base.txt`, parse policy chunks,
   and apply deterministic eligibility filtering.
3. **Semantic retrieval (complete)** - embeddings, cosine similarity, Top-K behavior,
   retrieval evaluation data, and the custom retrieval tool.
4. **Agent workflow** - Data Retriever, Report Generator, explicit graph state,
   sequential LangGraph orchestration, and CLI smoke scenarios.
5. **Evaluation and observability** - retrieval metrics, groundedness cases,
   LangSmith tracing, and graph inspection.
6. **Demo and presentation** - lightweight profile-selector UI, screenshots,
   reviewer documentation, limitations, and final regression review.

Each roadmap item requires its own inspect-plan-implement-test-review cycle.
Do not advance while the current layer has unresolved verification failures.
