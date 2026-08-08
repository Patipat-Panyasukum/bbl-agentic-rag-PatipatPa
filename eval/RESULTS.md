# Retrieval Evaluation Results

## Executed baseline

- Date: 2026-08-08
- Python: 3.13.5
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Similarity: cosine
- Minimum similarity: `0.25`
- Top-K: `3`
- Dataset: 13 committed cases (11 positive, 2 expected-no-evidence)
- Command: `python scripts/evaluate_retrieval.py`

| Metric | Result |
| --- | ---: |
| Hit@1 | 1.000 |
| Hit@3 | 1.000 |
| MRR | 1.000 |
| No-evidence accuracy | 1.000 |

All cases passed. The cases cover direct and paraphrased OPD, inpatient, dental,
annual-leave, and international-travel queries across E001/JL3, E002/JL6, and
E003/JL9. The two negative cases verify that an ineligible international-travel
question and an unsupported parking question return no evidence at the selected
threshold.

## Limitations

This is a small, curated English-language dataset derived from the demo policy
text, so perfect scores do not imply production retrieval quality. Future
iterations should add harder paraphrases, Thai-language queries, ambiguous
questions, policy revisions, and human-reviewed relevance judgments.
