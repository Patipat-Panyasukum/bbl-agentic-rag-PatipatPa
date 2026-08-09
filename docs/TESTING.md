# Testing Strategy

## Principles

- Test deterministic logic without LLM or network dependencies.
- Cover failure and boundary behavior as well as successful examples.
- Use fakes or controlled model responses for agent routing tests.
- Keep a small explicit retrieval evaluation set with expected policy IDs.
- Separate planned coverage from commands and results actually observed.

## Test levels

### Unit tests

Test deterministic components independently:

- employee lookup and unknown employee behavior
- policy parsing and malformed chunks
- policy prose remains free of retrieval metadata and custom block markers
- sidecar schema, missing section references, and source/metadata joining
- eligibility rules across employee metadata
- Chroma cosine-distance conversion, ordering, deterministic ties, and Top-K
- generated-index synchronization, stale-row removal, and embedding reuse
- vector metadata records the numbered-clause strategy and zero overlap
- empty candidates and irrelevant input

### Retrieval tests

Using fixed employees and expected policy IDs, verify that:

- a direct question retrieves the expected eligible policy
- paraphrases retrieve the same relevant policy
- the same question returns profile-appropriate evidence: E001/E002 share the
  JL2-JL8 General policy while E003 receives the Operations JL1 policy
- deterministic eligibility becomes Chroma's exact candidate-ID metadata filter
- a semantically stronger but ineligible vector cannot enter the ranked results
- an explicitly named job-level policy question selects source clauses whose
  policy range covers that level and marks whether each cited clause applies to
  the current profile
- the original wording, rather than an LLM reformulation, ranks an explicit
  policy-scope question so the agent cannot change its subject
- unsupported questions return no usable evidence

Embedding-dependent tests should control the embedding model or mark slow/model
tests separately so normal unit runs remain deterministic.

### Agent tests

Verify with controlled models and tool spies that:

- the Data Retriever calls the retrieval tool rather than answering directly
- trusted employee context cannot be replaced by model-generated tool input
- the retriever returns raw evidence into graph state
- the Report Generator receives the question and retrieved evidence
- the Report Generator answers the policy question before a deterministic
  current-profile applicability note is appended; internal policy citations are
  exposed through structured output while the final answer renders readable
  source labels
- the Report Generator has no tools and does not add unsupported policy facts
- empty evidence produces the agreed insufficient-information response

### Graph and integration tests

Exercise the complete sequence:

```text
Employee Context
  -> Data Retriever Agent
  -> Retrieval Tool
  -> Policy Evidence
  -> Report Generator Agent
  -> Final Answer
```

Assert state at node boundaries, node order, successful personalized answers,
unknown employees, empty retrieval, and controlled downstream failures.

### Smoke tests

Maintain representative end-to-end examples for:

- a normal benefit query
- the same query under different employee profiles
- a paraphrased query
- an unknown or unsupported policy question

The unsupported case passes only when the answer explicitly says that the
available policy evidence is insufficient and contains no invented entitlement.

### Demo UI tests

The frontend verification is split by cost:

- `npm run lint`, `npm run typecheck`, and `npm run build` validate source and
  production compilation without model calls.
- `npm run ui:smoke` renders desktop/mobile layouts, signs into a fictional
  profile, verifies the local graph connection, opens the profile-scoped Chat
  history route, exercises profile switching, checks console errors, and
  captures login/empty-state screenshots.
- `LIVE_UI_SMOKE=1` sends the natural Thai E001 OPD question through the Agent
  Chat UI, asserts the grounded `14,250`-baht answer and expected OPD policy,
  verifies all four observable activity steps, exercises nested evidence and
  activity collapse plus the tool visibility control, verifies expanded
  evidence remains inside the scrollable message pane instead of overlapping
  the composer, then verifies a JL8 policy-scope answer includes both the OPD
  policy and deterministic E001/JL3 applicability. It then opens a real saved
  thread from Chat history and confirms the grounded answer renders again.
- `CAPTURE_ALL_DEMO=1` adds personalized E003 OPD, E002 IPD, and unsupported
  parking scenarios for reviewer screenshots.

Browser checks must assert that the stream has finished before capturing the
answer. Seeing the first streamed token is not a completed run.

### Agent workflow evaluation

The committed `eval/agent_cases.json` dataset evaluates the API-backed graph as
a black box. It scores evidence selection, structured required citations,
explicit answer facts, answer language, the graph grounding flag, and exact
abstention behavior. Provider errors are recorded per case so one failure does
not hide later cases.

Run a low-cost canary before the complete set:

```powershell
python scripts/evaluate_agents.py --limit 1
python scripts/evaluate_agents.py
```

The evaluator is deterministic after the model returns; it does not add another
LLM-as-judge call. Current executed results are recorded in
[the agent evaluation report](../eval/AGENT_RESULTS.md).

## Retrieval evaluation

Each evaluation example contains a query, employee ID, and one or more expected
policy IDs. Report at least:

- **Hit@1:** fraction of queries where a relevant policy is ranked first.
- **Hit@K:** fraction where any relevant policy appears in the first K results.
- **MRR:** mean reciprocal rank of the first relevant policy; a miss contributes
  zero.

The personal-retrieval evaluation runs after eligibility filtering, so an
ineligible match never counts as a personal result. Policy-scope behavior is
evaluated in the full agent workflow because it deliberately returns source
policy information plus a separate applicability flag. Keep both datasets
small, readable, and committed so reviewers can reproduce the score.

## Reporting results

For every completed slice, record:

- exact command
- pass/fail/skip counts or metric values
- relevant environment/model details
- limitations, flakes, and untested paths

Use labels such as **Planned**, **Executed**, and **Not yet available**. Never
turn a planned test into a claimed result or call "no tests collected" a pass.

## Current implemented coverage

The deterministic suite covers employee lookup, policy parsing failures, every
eligibility dimension, employee-specific OPD results, paraphrases, the Chroma
metadata candidate boundary, cosine-distance conversion, persistent-record
reuse, stale-row cleanup, chunk metadata, Top-K, irrelevant queries, tool-schema
identity protection, tool artifacts, dataset validation, and metric calculation.

The OpenAI embedding evaluation uses 16 committed English/Thai cases and
currently records Hit@1 `1.000`, Hit@3 `1.000`, MRR `1.000`, and no-evidence
accuracy `1.000`. See [the evaluation report](../eval/RESULTS.md) for
configuration and limitations.

Agent and graph coverage verifies forced retrieval-tool use, model-visible tool
arguments, no direct Retriever answer, evidence delivery to the Report
Generator, policy-first answer ordering with deterministic personal
applicability, unknown citations/numeric hallucination rejection, no-evidence
abstention without an LLM call, state propagation, node presence, unknown
employee short-circuiting, and personalized E001/E002/E003 graph results.

API-backed smoke verification is deliberately separate from pytest. It checks
provider compatibility and real prompt/tool behavior while keeping normal tests
fast, deterministic, and free of API cost.

The UI additionally verifies the Agent Chat `messages` input contract. The
graph must return the real Retriever `AIMessage` tool call, matching
`ToolMessage`, final answer message, employee context, and evidence state; the
UI must not synthesize fake tool activity.

The UI renders only actual graph messages and observable tool data. It must not
request, persist, synthesize, or display private model reasoning.

The full-workflow dataset currently contains 12 English/Thai cases, including
an explicit JL8 policy-scope question with a separate E001/JL3 applicability
note. Its executed baseline is `1.000` for evidence, citation, required-fact,
language, grounding, abstention, and overall accuracy. This is a small curated
baseline rather than a claim of production quality.
