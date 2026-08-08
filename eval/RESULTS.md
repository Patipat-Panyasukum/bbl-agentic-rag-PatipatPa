# Retrieval Evaluation Results

## Executed baseline

- Date: 2026-08-08
- Python: 3.13.5
- Embedding model: OpenAI `text-embedding-3-small`
- Source: sanitized policy prose in `knowledge_base.txt`
- Derived retrieval metadata: `policy_metadata.json`
- Vector store: persistent local Chroma, cosine collection
- Chunking: natural numbered policy clauses, overlap `0`
- Candidate filter: deterministic eligible policy IDs via Chroma metadata `$in`
- Similarity: `1 - Chroma cosine distance`
- Minimum similarity: `0.26`
- Top-K: `3`
- Dataset: 15 committed cases (13 positive, 2 expected-no-evidence)
- Command: `python scripts/evaluate_retrieval.py`
- Outcome: all 15 cases passed their Top-3/no-evidence expectations

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

## Threshold calibration

The cutoff is evaluated against observed scores, not chosen from the apparent
absolute size of a cosine value. Across the original retrieval cases, the
lowest relevant score was `0.321883` and the highest unsupported score was
`0.242074`. A full-workflow regression case exposed a harder English emergency
ambulance query: its correct first-ranked policy scores `0.265540`. That case is
now also committed to the retrieval dataset. The retained `0.26` cutoff admits
it while rejecting both unsupported cases; `0.27` would create a known false
negative.

## Limitations

This is a small curated dataset based on one sanitized medical-benefit policy.
Bilingual search terms in the sidecar are human-authored for these policy
sections and help English questions match Thai source text; they are retrieval
hints, not policy evidence. Perfect scores do not imply production retrieval
quality. The full graph is evaluated separately in
[the agent workflow report](AGENT_RESULTS.md). Future work should still add
harder paraphrases, policy revisions, human relevance judgments, repeated model
runs, and model comparisons.
