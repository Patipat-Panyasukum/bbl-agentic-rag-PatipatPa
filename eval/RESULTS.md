# Retrieval Evaluation Results

## Executed baseline

- Date: 2026-08-08
- Python: 3.13.5
- Embedding model: OpenAI `text-embedding-3-small`
- Source: sanitized policy prose in `knowledge_base.txt`
- Derived retrieval metadata: `policy_metadata.json`
- Similarity: cosine
- Minimum similarity: `0.26`
- Top-K: `3`
- Dataset: 14 committed cases (12 positive, 2 expected-no-evidence)
- Command: `python scripts/evaluate_retrieval.py`
- Outcome: all 14 cases passed their Top-3/no-evidence expectations

| Metric | Result |
| --- | ---: |
| Hit@1 | 1.000 |
| Hit@3 | 1.000 |
| MRR | 1.000 |
| No-evidence accuracy | 1.000 |

The dataset covers English and Thai OPD, IPD, hospital-room, eligibility,
social-security-first, Day Case, ambulance, and overseas-accident questions
across E001/JL3 General, E002/JL6 General, and E003/JL1 Operations. Annual-leave
and parking questions verify that unsupported topics return no evidence at the
selected threshold.

## Limitations

This is a small curated dataset based on one sanitized medical-benefit policy.
Bilingual search terms in the sidecar are human-authored for these policy
sections and help English questions match Thai source text; they are retrieval
hints, not policy evidence. Perfect scores do not imply production retrieval
quality. A later evaluation slice should add harder paraphrases, ambiguous
questions, policy revisions, human relevance judgments, and model comparisons.
