# Implementation Plan

## Current state

- Branch: `feat/evaluation-observability`, based on merged
  `feat/langgraph-agents`.
- Implemented runtime layers: deterministic employee context, eligibility-first
  semantic retrieval, two agents, sequential LangGraph, CLI, and smoke cases.
- Active branch outcome: agent evaluation, query-drift protection, LangSmith
  trace labels, and compiled graph artifacts are complete and verified.

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
- [x] Seed fictional E001/JL3 General, E002/JL6 General, and E003/JL1
  Operations records in local SQLite.
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
  E002, and E003: passed with the expected JL3, JL6, and JL1 contexts.
- Repeated default seeding retained exactly three employee rows; `pip check`
  reported no broken requirements.
- `git diff --check`, changed-file whitespace/newline checks, Markdown link
  checks, secret scan, and scope scan: passed. Generated database, cache, and
  editable-install metadata remain ignored.

## Active branch outcome: core RAG

Status: **complete (2026-08-08)**

- [x] Author 12 local policies with explicit eligibility metadata.
- [x] Parse numbered source sections and join validated retrieval metadata.
- [x] Filter country, company, employee type, and job level before embeddings.
- [x] Implement sentence embeddings, cosine similarity, thresholding, and Top-K.
- [x] Expose an employee-bound custom LangChain retrieval tool.
- [x] Add deterministic parser, eligibility, retrieval, tool, and metric tests.
- [x] Add and execute a real-model retrieval evaluation.
- [x] Complete full regression, diff review, and branch documentation review.

### Evaluation record

- Current model: OpenAI `text-embedding-3-small`.
- Configuration: cosine similarity, minimum score `0.26`, Top-3.
- Dataset: 12 positive and two expected-no-evidence English/Thai cases.
- Result: Hit@1 `1.000`, Hit@3 `1.000`, MRR `1.000`, no-evidence accuracy
  `1.000`; all 14 Top-3/no-evidence expectations passed.

### Verification record

- `python -m pytest -q --basetemp=.pytest_cache\\core-final`: 46 tests passed
  in 0.40 seconds.
- `python scripts/evaluate_retrieval.py`: all 14 cases passed with the recorded
  OpenAI embedding metrics.
- `python -m compileall -q src scripts tests` and `pip check`: passed.
- JSON parsing, policy/evaluation counts, Markdown links, whitespace/newlines,
  `git diff --check`, ignored-artifact checks, TODO/secret scan, and scope review:
  passed.

## Active branch outcome: agent workflow

Status: **complete (2026-08-08)**

- [x] Force the Data Retriever Agent to call the employee-bound retrieval tool.
- [x] Execute retrieval in a distinct graph node and pass structured evidence.
- [x] Implement a tool-free Report Generator with grounding safeguards.
- [x] Add explicit typed graph input, state, output, and sequential node edges.
- [x] Add configurable OpenAI-compatible model settings and LangGraph config.
- [x] Add CLI and representative API-backed smoke scenarios.
- [x] Test agent responsibilities, failure cases, and E001/E002/E003 integration.
- [x] Complete full regression, final diff review, and documentation validation.

### API-backed verification record

- `langgraph validate`: configuration valid; one graph discovered.
- Full `run_smoke_queries.py`: all five API-backed cases passed. The run covered
  E001/JL3 General OPD, E003/Operations JL1 OPD, a Thai E002 IPD question, the
  Thai social-security-first rule, and unsupported parking abstention.

### Automated verification record

- Focused agent/graph tests: 18 passed after input and tool-query hardening.
- `python -m pytest -q --basetemp=.pytest_cache\\langgraph-final-2`: 68 tests
  passed in 4.05 seconds.
- `langgraph validate`: configuration valid with one graph discovered.
- `python -m compileall -q src scripts tests` and `pip check`: passed.
- Python line length/whitespace, JSON parsing, Markdown links, `git diff --check`,
  TODO/secret scan, generated-artifact ignore checks, and stale-documentation
  scan: passed.

## Active revision: sanitized medical policy and OpenAI embeddings

Status: **complete (2026-08-08)**

- [x] Inspect the supplied Thai medical-benefit extraction.
- [x] Exclude names, signatures, organization branding, approval details,
  extraction metadata, masks, struck-through text, and corrupted OCR repeats.
- [x] Replace invented benefits with sanitized medical-policy prose and 12
  neutral `DEMO` retrieval mappings.
- [x] Keep policy prose in `knowledge_base.txt` and derived section mappings,
  search terms, and eligibility rules in `policy_metadata.json`.
- [x] Align fictional employees with JL2-JL8 General and Operations JL1 scope.
- [x] Replace the local embedding dependency with OpenAI
  `text-embedding-3-small` while keeping deterministic tests offline.
- [x] Add English/Thai retrieval cases and API-backed smoke scenarios.
- [x] Measure and tune the relevance threshold using actual similarity scores.
- [x] Complete full regression, diff/secret/brand review, and documentation
  validation.

### Verification record

- Focused policy/embedding/agent/graph tests: 61 passed in 3.89 seconds.
- Focused source/sidecar parser and retrieval tests: 46 passed in 3.80 seconds.
- OpenAI retrieval evaluation: all 14 cases passed; Hit@1 `1.000`, Hit@3
  `1.000`, MRR `1.000`, and no-evidence accuracy `1.000`.
- API-backed LangGraph smoke run: all five General/Operations, English/Thai,
  and unsupported cases passed.
- Full regression after source/metadata separation: 76 tests passed in 3.94
  seconds.
- `python -m compileall -q src scripts tests`, `pip check`, and
  `langgraph validate`: passed; one graph discovered.
- JSON parsing, local Markdown links, `git diff --check`, ignore rules, and scans
  for secret shapes, source names, and source-organization branding: passed.

## Active revision: cost-efficient agent model

Status: **complete (2026-08-08)**

- [x] Change the shared Data Retriever and Report Generator default from
  `gpt-5.6-terra` to `gpt-5.6-luna`.
- [x] Preserve the Responses API, low reasoning effort, low verbosity, prompts,
  tool contract, grounding validation, and `text-embedding-3-small` retrieval.
- [x] Keep the model configurable through `OPENAI_MODEL` and document the
  cost-conscious default.
- [x] Verify the model with representative offline and API-backed checks.

### Verification record

- Runtime configuration resolved to `gpt-5.6-luna`, Responses API enabled, and
  low reasoning effort.
- Focused configuration/agent/graph tests: 23 passed in 3.96 seconds.
- API-backed one-case canary: passed before the full smoke run.
- API-backed LangGraph smoke run: all five English/Thai, General/Operations,
  and unsupported-information cases passed with expected evidence and citations.
- Full regression: 76 tests passed in 3.98 seconds.
- `python -m compileall -q src scripts tests`, `pip check`, `langgraph validate`,
  `git diff --check`, and stale-model-reference scan: passed.

## Active branch outcome: evaluation and observability

Status: **complete (2026-08-08)**

- [x] Add a committed 10-case full-workflow dataset and deterministic evaluator.
- [x] Score evidence, citations, required facts, language, grounding, abstention,
  and overall case success without adding an LLM judge.
- [x] Add inherited LangSmith run names, source/case tags, and safe metadata to
  CLI, smoke, and evaluation invocations.
- [x] Export Mermaid and PNG artifacts from the compiled graph.
- [x] Use measured failures to anchor agent queries to the original question and
  pin Report Generator language/evidence-selection behavior.
- [x] Document local evaluation, trace inspection, data handling, results, and
  limitations.

### Evaluation and verification record

- Initial full-workflow evaluation: 8 of 10 cases passed. It exposed generic
  query drift on annual leave and an ambiguous overseas reference case.
- Final API-backed agent evaluation after targeted fixes: all 10 cases passed;
  evidence, citation, required-fact, language, grounding, abstention, and overall
  accuracy were each `1.000`.
- OpenAI retrieval evaluation: all 14 cases passed; Hit@1 `1.000`, Hit@3 `1.000`,
  MRR `1.000`, and no-evidence accuracy `1.000`.
- Full regression: 93 tests passed in 6.92 seconds.
- LangSmith read-back: a successful `benefitwise.evaluation` root contained the
  four graph nodes plus nested Retriever model, retrieval tool, and Report
  Generator model runs with the expected case metadata.
- Compiled graph export wrote validated Mermaid source and a 16,165-byte PNG;
  the generated image was visually inspected.
- `python -m compileall -q src scripts tests`, `pip check`, and
  `langgraph validate`: passed; one graph discovered.

## Active revision: local persistent Chroma retrieval

Status: **complete (2026-08-08)**

- [x] Add a local persistent Chroma index without introducing hosted
  infrastructure.
- [x] Keep employee eligibility deterministic and pass only admitted policy IDs
  into Chroma's metadata filter before cosine ranking.
- [x] Synchronize only new/changed generated vectors and remove stale index rows.
- [x] Record natural numbered-clause chunking with overlap `0` and document why
  arbitrary token overlap is not useful for the current short coherent clauses.
- [x] Preserve raw policy evidence, original-question anchoring, and grounded
  insufficient-information behavior.
- [x] Calibrate the existing threshold against positive, negative, and boundary
  cases rather than changing it based on its absolute value.
- [x] Keep generated vector data and Chroma telemetry local and untracked.

### Evaluation and verification record

- Installed Chroma `1.5.9` under Python 3.13.5. OpenTelemetry packages were
  aligned with the existing LangGraph API; `pip check` reports no broken
  requirements.
- Focused Chroma/retrieval/config/tool tests: 31 passed in 4.34 seconds.
- Full deterministic regression:
  `python -m pytest --basetemp=.pytest_cache\\tmp\\chroma-full-3 -q` passed all
  97 tests in 4.99 seconds.
- OpenAI retrieval evaluation: all 15 committed cases passed; Hit@1 `1.000`,
  Hit@3 `1.000`, MRR `1.000`, and no-evidence accuracy `1.000`.
- Measured scores included relevant floor `0.321883`, unsupported ceiling
  `0.242074`, and the harder English ambulance positive at `0.265540`.
  Therefore `0.26` remains the measured cutoff; `0.27` would reject that known
  relevant case.
- `langgraph validate` passed with one graph. A live Luna canary passed evidence,
  citation, required-fact, language, grounding, and overall checks at `1.000`.
- `python -m compileall -q src scripts tests`, `pip check`, and
  `git diff --check` passed. All local links across 10 Markdown files resolve;
  JSON inputs parse; `.env`, `.venv/`, `.codex/`, SQLite, and `data/chroma/`
  remain ignored; no populated API-key shape was found in the diff.

## Next branch: demo UI and presentation

After review and merge, create `feat/demo-ui` from updated `main`. Add a
lightweight fictional profile selector, reviewer screenshots, final README
requirement mapping, limitations, and presentation cleanup.

## Incremental roadmap

1. **Employee context (complete)** - package structure, SQLite seed, deterministic lookup,
   and unit tests.
2. **Policy foundation (complete)** - author `knowledge_base.txt`, parse policy chunks,
   and apply deterministic eligibility filtering.
3. **Semantic retrieval (complete)** - embeddings, cosine similarity, Top-K behavior,
   retrieval evaluation data, and the custom retrieval tool.
4. **Agent workflow (complete)** - Data Retriever, Report Generator, explicit graph state,
   sequential LangGraph orchestration, and CLI smoke scenarios.
5. **Evaluation and observability (complete)** - retrieval/agent metrics,
   groundedness cases, labeled LangSmith tracing, and compiled graph inspection.
6. **Demo and presentation** - lightweight profile-selector UI, screenshots,
   reviewer documentation, limitations, and final regression review.

Each roadmap item requires its own inspect-plan-implement-test-review cycle.
Do not advance while the current layer has unresolved verification failures.
