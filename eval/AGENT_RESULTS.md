# Agent Workflow Evaluation Results

## Executed baseline

- Date: 2026-08-09
- Chat model: OpenAI `gpt-5.6-luna`
- API mode: Responses API
- Reasoning effort: `low`
- Embedding model: OpenAI `text-embedding-3-small`
- Retrieval configuration: cosine similarity, minimum original-query score
  `0.26`, best-score query fusion, Top-3
- Dataset: 12 committed cases (10 answerable, 2 expected abstentions), including
  an explicit JL8 policy-scope question followed by E001/JL3 applicability
- Command: `python scripts/evaluate_agents.py`
- Citation output: validated policy IDs are returned in structured
  `citation_policy_ids`; final answers render reader-facing policy-section labels
  instead of internal IDs
- Outcome: all 12 cases passed every required contract

| Metric | Result |
| --- | ---: |
| Evidence accuracy | 1.000 |
| Citation accuracy | 1.000 |
| Required-fact accuracy | 1.000 |
| Language accuracy | 1.000 |
| Grounding pass rate | 1.000 |
| Abstention accuracy | 1.000 |
| Overall pass rate | 1.000 |

The dataset covers General and Operations employees, English and Thai answers,
an explicit JL8 policy question plus a separate current-profile note, OPD/IPD
limits, social-security precedence, Day Case treatment, ambulance coverage,
claim documents, overseas treatment, and unsupported annual-leave and parking
questions.

The natural Thai OPD regression retrieves `MED-OPD-GENERAL-JL2-8` at rank 1
and answers with `14,250 บาทต่อปี`; it was added after that policy had appeared
at rank 5 and fallen outside the graph's Top-3 evidence window.

## What the evaluation exposed

The first full run passed 8 of 10 cases. It exposed a generic term added during
annual-leave query reformulation and an ambiguous overseas reference question.
The retrieval boundary requires candidate evidence to clear the relevance
threshold against the original user question, then ranks with the better of the
agent-query and original-query scores. The overseas case now distinguishes
illness from the separate accident rule.

A later repeated run exposed a harmless ambulance-query rewording that fell
below the cutoff even though the original question remained relevant. Best-score
fusion now tolerates that variance without letting an unsupported original
question admit evidence.

A later run exposed language switching when English questions were paired with
Thai policy evidence. The Report Generator request now carries a deterministic
required-language label and explicit instructions for selecting the relevant
item from Top-K evidence. A policy-scope regression then showed that a model
reformulation could rank IPD ahead of an explicitly requested OPD fact. Explicit
JL-audience questions now rank by the original wording, and the application
appends the current-profile applicability note deterministically. A later
reader-facing revision keeps policy IDs in structured output for grounding and
evaluation while rendering source labels in the final answer; it also instructs
the Generator not to infer that a prerequisite is unnecessary merely because
the retrieved evidence omits it. The result above is the subsequent executed
baseline.

## Limitations

This is a small curated dataset derived from one sanitized medical policy. The
required-fact checks use explicit reference terms and deterministic structured
citations;
they are not a substitute for human review or a broader semantic correctness
judge. A single perfect run does not eliminate model variance. Production
evaluation should add repeated trials, adversarial prompts, more policy
families, policy-version tests, latency/token budgets, and human judgments.
