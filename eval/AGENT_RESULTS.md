# Agent Workflow Evaluation Results

## Executed baseline

- Date: 2026-08-08
- Chat model: OpenAI `gpt-5.6-luna`
- API mode: Responses API
- Reasoning effort: `low`
- Embedding model: OpenAI `text-embedding-3-small`
- Retrieval configuration: cosine similarity, minimum score `0.26`, Top-3,
  original-query relevance anchor enabled
- Dataset: 10 committed cases (8 answerable, 2 expected abstentions)
- Command: `python scripts/evaluate_agents.py`
- Outcome: all 10 cases passed every required contract

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
OPD/IPD limits, social-security precedence, Day Case treatment, ambulance
coverage, claim documents, overseas treatment, and unsupported annual-leave and
parking questions.

## What the evaluation exposed

The first full run passed 8 of 10 cases. It exposed a generic term added during
annual-leave query reformulation and an ambiguous overseas reference question.
The retrieval boundary now requires candidate evidence to clear the relevance
threshold against both the agent search query and the original user question.
The overseas case now distinguishes illness from the separate accident rule.

A later run exposed language switching when English questions were paired with
Thai policy evidence. The Report Generator request now carries a deterministic
required-language label and explicit instructions for selecting the relevant
item from Top-K evidence. The result above is the subsequent executed baseline.

## Limitations

This is a small curated dataset derived from one sanitized medical policy. The
required-fact checks use explicit reference terms and deterministic citations;
they are not a substitute for human review or a broader semantic correctness
judge. A single perfect run does not eliminate model variance. Production
evaluation should add repeated trials, adversarial prompts, more policy
families, policy-version tests, latency/token budgets, and human judgments.
