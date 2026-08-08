# Technical Decisions

This is a lightweight decision log. Add an entry when a choice affects system
boundaries, dependencies, data contracts, evaluation, or reviewer-visible
behavior. Each entry records status, context, decision, and consequences.

## D001: Use a sequential two-agent LangGraph workflow

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** The assignment requires a Data Retriever and Report Generator.
- **Decision:** Orchestrate the retriever before the report generator with
  explicit evidence passed through graph state.
- **Consequences:** Responsibilities are easy to inspect and test. Extra agent
  hierarchies, loops, and Deep Agents are excluded unless a demonstrated need
  changes the decision.

## D002: Keep identity and eligibility outside the LLM

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Personalized answers must be reproducible and must not depend on
  an LLM inferring who the employee is.
- **Decision:** Resolve the employee ID from SQLite before agent execution and
  inject the trusted context into retrieval. Eligibility rules are deterministic.
- **Consequences:** The model may decide what to search for but cannot select or
  alter the profile that controls access to policies.

## D003: Filter eligibility before semantic ranking

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Semantically similar policy text may belong to a different job
  level, country, company, or employee type.
- **Decision:** Remove ineligible chunks first, then embed/rank the remaining
  candidates and apply Top-K.
- **Consequences:** Ineligible text cannot leak through similarity ranking.
  Retrieval evaluation must use the same ordering of operations.

## D004: Use local assignment-friendly data sources

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** The demo should be understandable and reproducible without
  production infrastructure.
- **Decision:** `knowledge_base.txt` is the required policy source and SQLite
  stores fictional employee records. Retrieval metadata is stored separately
  from policy prose. Generated database files stay untracked.
- **Consequences:** Data is easy to inspect and seed. Production persistence,
  synchronization, and SSO integration remain out of scope.

## D005: Use sentence embeddings and cosine similarity

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Queries should match paraphrased policy content without requiring
  a vector database.
- **Decision:** Rank eligible chunks with sentence embeddings, cosine similarity,
  and a deterministic Top-K limit.
- **Consequences:** Retrieval stays small and transparent. The exact embedding
  model and thresholds will be selected and measured in the retrieval slice.

## D006: Fail closed when policy evidence is absent

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** A fluent unsupported benefit answer would be misleading.
- **Decision:** The Report Generator may use only supplied evidence. Empty or
  insufficient evidence produces an explicit insufficient-information response.
- **Consequences:** Some questions will remain unanswered, but outputs are safer
  and groundedness can be tested directly.

## D007: Defer production infrastructure

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** This is a programming-test demonstration, not a production rollout.
- **Decision:** Do not add production authentication, hosted vector storage,
  network databases, or deployment infrastructure to the initial implementation.
- **Consequences:** Development remains focused. The README will describe likely
  production evolution separately from implemented capabilities.

## D008: Use strict text blocks and an employee-bound retrieval tool

- **Status:** Superseded by D014
- **Date:** 2026-08-08
- **Context:** Reviewers need to inspect the required text knowledge source,
  while the future retriever agent must not control employee identity.
- **Decision:** Parse explicit `[POLICY]` blocks from `knowledge_base.txt`, reject
  malformed metadata, and bind trusted `EmployeeContext` inside the LangChain
  tool. The model-visible schema contains only query and Top-K.
- **Consequences:** Policy content and access rules are transparent, and model
  tool calls cannot substitute another employee. The custom format is purposely
  small and would need versioning for production policy management.

## D009: Use a measured local retrieval baseline

- **Status:** Superseded by D013
- **Date:** 2026-08-08
- **Context:** Core retrieval needs a reproducible baseline before agent prompts
  can mask or amplify retrieval errors.
- **Decision:** Use `all-MiniLM-L6-v2`, cosine similarity, Top-3, and a `0.25`
  threshold for the initial English demo. Measure positive cases with Hit@K/MRR
  and negative cases with no-evidence accuracy.
- **Consequences:** The baseline is local and reproducible. The current perfect
  score applies only to the small curated dataset and must be re-evaluated when
  policies, languages, or queries change.

## D010: Separate agent planning from tool execution in graph state

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** The assignment requires the Retriever Agent to call the custom
  tool, while graph inspection should show evidence moving between stages.
- **Decision:** Force exactly one tool call from the Retriever Agent, store the
  validated call in explicit state, and execute it in a separate retrieval node
  using employee context rebuilt from trusted state.
- **Consequences:** The graph visibly preserves the required sequence and tests
  can prove tool use. The Retriever cannot answer directly or change identity.

## D011: Fail closed with deterministic grounding checks

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Prompt instructions alone cannot guarantee that generated policy
  claims remain supported.
- **Decision:** Skip the Report Generator when evidence is empty. For generated
  answers, require known policy citations and reject numeric claims absent from
  trusted employee context/evidence.
- **Consequences:** Unsupported output becomes an insufficient-information
  response. The lightweight validator is intentionally conservative and does
  not replace broader semantic groundedness evaluation.

## D012: Keep the API model and endpoint configurable

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** The assignment requests an OpenAI-compatible LLM and reviewers may
  use different provider endpoints or available models.
- **Decision:** Default to `gpt-5.6-luna` through the Responses API with low
  reasoning effort. Both agents have narrow responsibilities backed by
  deterministic tool, evidence, citation, and numeric-claim checks. Expose the
  model, base URL, API mode, reasoning, and verbosity through environment
  variables.
- **Consequences:** The default favors lower operating cost for this bounded
  workflow. Representative API-backed smoke cases must pass before treating
  Luna as verified; reviewers can select another compatible model without code
  changes.

## D013: Use a sanitized source policy and OpenAI embeddings

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** The demo needs a realistic Thai policy without exposing personal
  names, signatures, source-organization branding, or extraction artifacts. The
  retrieval model must support sentence/context similarity across English and
  Thai queries.
- **Decision:** Adapt only clearly readable rules from the supplied medical
  policy into neutral `DEMO` sections. Exclude personal/approval data, branding,
  OCR coordinates and IDs, masks, struck-through text, and corrupted repeated
  passages. Use OpenAI `text-embedding-3-small`, cosine similarity, Top-3, and a
  measured `0.26` threshold.
- **Consequences:** The knowledge base is realistic but explicitly not an
  official policy copy. Retrieval evaluation now requires an OpenAI API key and
  incurs small API usage. Deterministic tests remain offline through an injected
  embedding fake.

## D014: Separate policy prose from retrieval metadata

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Real policy documents do not contain application fields such as
  `min_job_level`, `companies`, or custom `[POLICY]` delimiters. Mixing those
  fields into `knowledge_base.txt` made the source look synthetic and blurred
  the source-of-truth boundary.
- **Decision:** Keep sanitized numbered policy prose in `knowledge_base.txt`.
  Maintain section mappings, stable policy IDs, bilingual search terms, and
  eligibility rules in `policy_metadata.json`. Validate and join both files at
  ingestion. Search terms may affect embeddings but are excluded from evidence.
- **Consequences:** Reviewers can inspect a realistic policy document separately
  from metadata derived by the application team. Metadata must be maintained
  when source section numbering or demo eligibility changes, and validation
  fails closed if a mapping points to a missing section.
