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
- eligibility rules across employee metadata
- cosine-similarity ordering, ties, and Top-K limits
- empty candidates and irrelevant input

### Retrieval tests

Using fixed employees and expected policy IDs, verify that:

- a direct question retrieves the expected eligible policy
- paraphrases retrieve the same relevant policy
- the same question returns different eligible evidence for E001, E002, and E003
- ineligible policies are removed before semantic ranking
- unsupported questions return no usable evidence

Embedding-dependent tests should control the embedding model or mark slow/model
tests separately so normal unit runs remain deterministic.

### Agent tests

Verify with controlled models and tool spies that:

- the Data Retriever calls the retrieval tool rather than answering directly
- trusted employee context cannot be replaced by model-generated tool input
- the retriever returns raw evidence into graph state
- the Report Generator receives the question and retrieved evidence
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

## Retrieval evaluation

Each evaluation example contains a query, employee ID, and one or more expected
policy IDs. Report at least:

- **Hit@1:** fraction of queries where a relevant policy is ranked first.
- **Hit@K:** fraction where any relevant policy appears in the first K results.
- **MRR:** mean reciprocal rank of the first relevant policy; a miss contributes
  zero.

Evaluation must run after eligibility filtering so an ineligible match never
counts as relevant. Keep the dataset small, readable, and committed so reviewers
can reproduce the score.

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
eligibility dimension, employee-specific OPD results, paraphrases, filtering
before embedding, cosine/zero-vector behavior, Top-K, irrelevant queries,
tool-schema identity protection, tool artifacts, dataset validation, and metric
calculation.

The real-model evaluation uses 13 committed cases and currently records Hit@1,
Hit@3, MRR, and no-evidence accuracy of `1.000`. See
[the evaluation report](../eval/RESULTS.md) for configuration and limitations.
