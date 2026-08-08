# Agent Guidance

This repository is developed in small, verified increments. Start with
[PLANS.md](PLANS.md), then use these sources of truth:

- [Architecture](docs/ARCHITECTURE.md) for boundaries and data flow.
- [Development](docs/DEVELOPMENT.md) for setup and the engineering loop.
- [Testing](docs/TESTING.md) for test levels and evidence requirements.
- [Decisions](docs/DECISIONS.md) for accepted trade-offs.

For every meaningful task: inspect, plan the smallest useful slice, implement
focused changes, run narrow then broader checks, review the diff, evaluate AI
behavior when applicable, and update affected documentation. Record commands
and actual results; never report that something merely "should work."

Preserve these boundaries:

- Resolve employee identity and eligibility deterministically outside the LLM.
- The Data Retriever must call the retrieval tool and return evidence, not an
  end-user answer.
- The Report Generator receives retrieved evidence and has no tools.
- Filter by eligibility before semantic ranking and fail closed when evidence
  is absent.

Avoid unrelated refactors and unnecessary infrastructure. Never commit `.env`,
credentials, virtual environments, generated databases, or local agent config.
