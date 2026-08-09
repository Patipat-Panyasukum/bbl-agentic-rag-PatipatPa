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
- **Decision:** Resolve eligible policy IDs in application code, pass those IDs
  into the vector query as an exact metadata candidate filter, then apply
  cosine ranking and Top-K only within that set. The generated index may
  precompute embeddings for all sanitized demo policies.
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

- **Status:** Superseded by D017
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
  trusted employee context/evidence. Preserve validated citation IDs in
  structured graph output, but render policy-section labels rather than internal
  IDs in the employee-facing answer.
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

The threshold remains deliberately tied to evaluation rather than its apparent
absolute size. The current English emergency-ambulance case scores `0.265540`,
while unsupported annual leave tops out at `0.242074`; raising the cutoff to
`0.27` would discard a correctly ranked positive case.

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

## D015: Anchor agent searches to the original question

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Full-workflow evaluation found that a valid but generic word added
  during agent query reformulation could push an unsupported annual-leave query
  above the retrieval threshold.
- **Decision:** When the Data Retriever reformulates a search, require candidate
  policy evidence to clear the similarity threshold against the original user
  question. Rank admitted candidates with the better of the model-query and
  original-query scores. Keep the original question bound inside the tool rather
  than exposing it as a model-controlled argument.
- **Consequences:** The model still decides what to search for, while semantic
  query drift fails closed. Harmless reformulation variance cannot suppress a
  policy already supported by the original question. The two query embeddings
  share one batch request; direct retrieval is unchanged without an anchor.

## D016: Prefer deterministic local agent evaluation with labeled traces

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Retrieval metrics alone do not test tool-driven query changes,
  answer citations, required facts, language, or grounded abstention. Adding an
  LLM judge would increase cost and variance for a small assignment baseline.
- **Decision:** Commit explicit full-workflow cases and score observable output
  contracts deterministically. Add source and case labels through
  `RunnableConfig` so the same runs are inspectable in LangSmith.
- **Consequences:** Results are inexpensive to interpret and regressions map to
  concrete contracts. Substring facts cannot judge semantic completeness, so
  human review or a separately evaluated judge remains future production work.

## D017: Persist policy vectors in local Chroma

- **Status:** Accepted
- **Date:** 2026-08-08
- **Context:** Re-embedding every policy clause on every query wastes API calls,
  and the retrieval boundary should make metadata filtering inspectable in the
  vector query without adding a hosted service.
- **Decision:** Use an ignored local Chroma persistent client configured for
  cosine distance. Index the natural numbered policy clauses with
  `text-embedding-3-small`, fingerprint generated records for incremental
  synchronization, and constrain every similarity query with an eligible
  `policy_id $in [...]` metadata filter computed from trusted employee context.
  Keep clause-level chunk overlap at `0` because each current rule is already a
  short, coherent 208-550-character unit.
- **Consequences:** Policy embeddings survive process restarts and unchanged
  clauses incur no repeat embedding cost. Chroma adds a local dependency and
  generated `data/chroma/` state, which remains ignored and rebuildable from
  `knowledge_base.txt` plus `policy_metadata.json`. Hosted vector
  infrastructure remains unnecessary for this assignment-scale corpus.

## D018: Customize Agent Chat UI around a fictional trusted session

- **Status:** Accepted
- **Date:** 2026-08-09
- **Context:** The assignment requires inspectable agent orchestration and final
  output screenshots. A generic chat client hides employee eligibility context,
  while building an unrelated chat transport would duplicate LangGraph's stream
  and tool-call behavior.
- **Decision:** Use LangChain's open-source Agent Chat UI as the frontend base
  and retain its standard single-column conversation and real tool-call/result
  rendering. Add only a fictional E001/E002/E003 sign-in and a compact employee
  avatar with a hover/click profile card. Group observable employee-context,
  Retriever, tool-result, and Report Generator events into one collapsible
  activity log without exposing private reasoning. Extend the existing graph
  with an optional `messages` contract so the CLI and UI share the same four
  nodes. Keep profile selection in local browser state, resolve authoritative
  context from SQLite on every run, and accept no API secrets in the browser.
- **Consequences:** Reviewers can trace the Retriever tool output into the
  Report Generator in both Studio and the UI. The sign-in is explicitly a demo
  session rather than security; production SSO, authorization, and server-side
  sessions remain out of scope. Frontend dependencies, Node verification, and
  browser smoke checks are now part of the submission surface.

## D019: Answer explicit policy audiences before current-profile applicability

- **Status:** Accepted
- **Date:** 2026-08-09
- **Context:** Filtering every question exclusively by the selected employee
  profile made a question such as “what does JL8 receive?” appear unanswered
  or let an LLM phrase the policy answer as if typed JL8 were the current
  employee identity. A policy question and a personal-entitlement question are
  related but not identical.
- **Decision:** Keep the eligibility-first retrieval lane for normal personal
  questions. When the original question explicitly names a JL audience, select
  policy source clauses whose metadata range covers that level and rank them by
  the original question, not a model reformulation. Attach a deterministic
  `applies_to_current_employee` flag to every result. The Report Generator
  answers the policy question from cited evidence; the application appends a
  separate concise applicability note for the selected profile and renders
  reader-facing source labels from validated citation IDs.
- **Consequences:** Policy facts remain answerable even when the current profile
  differs from the policy audience, while no typed text can override trusted
  identity. The evidence contract and tool display now expose applicability.
  Evaluation must cover both personal eligibility-first retrieval and explicit
  policy-scope behavior.

## D020: Show saved LangGraph threads as profile-scoped chat history

- **Status:** Accepted
- **Date:** 2026-08-09
- **Context:** Reviewers need to revisit actual tool/evidence conversations
  without the UI inventing a separate browser-only conversation log.
- **Decision:** Search the existing local LangGraph thread store from the
  frontend, derive only the latest user question, final answer, status, and
  update time for display, and filter each list to the selected fictional
  employee ID preserved in graph state. Use the original thread ID to reopen a
  conversation. Use the supplied BenefitWise mark and generated fictional
  avatars only as presentation assets.
- **Consequences:** History remains an inspectable view of actual graph data and
  avoids exposing private reasoning. This is local-demo persistence only;
  production retention, authorization, real employee imagery, and audit-log
  requirements remain deliberately out of scope.
