# V2 Implementation Delta: From MVP RAG to Agentic Graph-RAG

This document defines the exact file-by-file delta to evolve the current codebase into an enterprise-ready Agentic Graph-RAG system.

## 1) Target capabilities

1. Markdown-aware, hierarchy-preserving ingestion.
2. Hybrid retrieval: vector + graph traversal.
3. Intent router agent selecting retrieval strategy.
4. Dual-model orchestration (router/judge + generator).
5. Self-RAG critic loop before final answer.
6. Out-of-domain guardrails and refusal path.
7. Streaming token responses in API and UI.
8. Claim-linked evidence and transparent citations.
9. User feedback loop for answer quality.

## 2) New architecture components

- Ingestion pipeline:
- Parse markdown structure and preserve section lineage.
- Extract entities and relationships from chunks.

- Retrieval layer:
- Vector retrieval from existing store.
- Graph retrieval over entity graph.
- Hybrid merge/rerank of contexts.

- Agentic orchestration:
- Router model classifies query route (`vector`, `graph`, `hybrid`, `clarify`, `reject`).
- Generator model drafts answer.
- Critic model validates grounding and can trigger regeneration.

- API layer:
- Streaming endpoint for chat output.
- Non-stream endpoint preserved for compatibility.

- Frontend:
- Streaming render.
- Feedback buttons and telemetry hook.

## 3) File-by-file delta

### 3.1 Config and models

1. Update `backend/app/core/config.py`
- Add model provider keys for router/generator/critic.
- Add graph backend settings.
- Add guardrail thresholds and rerank weights.

Suggested keys:
- `router_provider`, `router_model`
- `generator_provider`, `generator_model`
- `critic_provider`, `critic_model`
- `graph_path` (local JSON graph fallback)
- `ood_similarity_threshold`
- `max_regeneration_attempts`
- `hybrid_vector_weight`, `hybrid_graph_weight`

2. Update `backend/app/models/schemas.py`
- Add explicit message schema for history.
- Add `route`, `confidence`, `trace_id`, `feedback_token` fields.
- Add `evidence` object with claim-to-source mapping.
- Add request flag `stream: bool`.

### 3.2 Ingestion and indexing

3. Add `backend/app/services/markdown_chunker.py`
- Parse markdown headers and emit section-aware chunks.
- Preserve metadata: `h1`, `h2`, `h3`, section path.

4. Update `backend/app/services/ingestion.py`
- Keep redirect support.
- Add content-type checks and extraction fallback.
- Return `resolved_url`, `raw_markdown` if available.

5. Add `backend/app/services/entity_extractor.py`
- Heuristic + model-assisted extraction of entities.
- Entity types: team, process, objective, tool, metric, timeline.

6. Add `backend/app/services/graph_store.py`
- Local graph storage (JSON) + optional Postgres tables.
- APIs:
- `upsert_entities_and_edges`
- `neighbors(entity, hops)`
- `search_entities(query)`

7. Update `scripts/build_index.py`
- Use markdown chunker.
- For each chunk:
- store vector embedding
- extract entities
- upsert graph nodes/edges

8. Update `scripts/sync_index.py`
- Incremental upsert for both vector and graph stores.
- On URL removal: delete vector chunks and graph references.

### 3.3 Retrieval and orchestration

9. Add `backend/app/services/router.py`
- Input: user question + optional history summary.
- Output: `route`, `reason`, `needs_clarification`, `ood`.

10. Add `backend/app/services/graph_retriever.py`
- Extract seed entities from query.
- Traverse graph and retrieve related evidence snippets.

11. Update `backend/app/services/retriever.py`
- Keep vector retrieval.
- Add hybrid retrieval orchestrator:
- vector-only
- graph-only
- merged hybrid with weighted rerank

12. Add `backend/app/services/critic.py`
- Validate answer claims against context.
- Return `pass/fail`, unsupported claims, recommended regeneration prompt.

13. Add `backend/app/services/orchestrator.py`
- Full request lifecycle:
- route -> retrieve -> generate -> critique -> regenerate if needed.
- Structured trace object for observability.

14. Update `backend/app/services/gemini_client.py`
- Keep current implementation but abstract to provider interface.
- Add `generate_stream` support if provider supports streaming.

15. Add `backend/app/services/groq_client.py`
- Router/judge low-latency model calls.
- Generation model calls with streaming.

16. Add `backend/app/services/llm_provider.py`
- Provider selection and model routing.
- Unified interfaces:
- `classify`
- `generate`
- `generate_stream`
- `judge`

### 3.4 API and frontend

17. Update `backend/app/api/chat.py`
- Move from direct retriever/generator to orchestrator.
- Add `POST /chat/stream` (SSE or chunked text).
- Return route and evidence in non-stream response.

18. Add `backend/app/api/feedback.py`
- Endpoint for thumbs up/down with optional comment.
- Persist to local JSON or Postgres table.

19. Update `frontend/src/api.js`
- Add stream client helper for `/chat/stream`.
- Add feedback submit helper.

20. Update `frontend/src/App.jsx`
- Stream tokens into active assistant bubble.
- Add route/transparency panel and source evidence links.
- Add feedback controls per assistant answer.

21. Add `frontend/src/components/` (new)
- `ChatMessage.jsx`
- `SourceList.jsx`
- `TraceBadge.jsx`
- `FeedbackButtons.jsx`

### 3.5 Guardrails and evaluation

22. Add `backend/app/services/guardrails.py`
- OOD detection using semantic score + route classifier.
- Policy responses for off-topic and unsafe prompts.

23. Update `scripts/evaluate.py`
- Add route accuracy metrics.
- Add grounding score metrics (claim support rate).
- Add guardrail pass rate.

24. Update `eval/questions.json`
- Add route label expectations and OOD cases.

### 3.6 Observability and ops

25. Add `backend/app/services/telemetry.py`
- Structured logs per request with `trace_id`.
- Latency timings by stage (route/retrieve/generate/critique).

26. Update `.github/workflows/ci.yml`
- Add lint/type-check stage.
- Add evaluation smoke stage (small subset).

27. Update `.github/workflows/sync-index.yml`
- Add graph sync sanity checks.
- Store sync report artifact.

28. Update `README.md`
- Add architecture diagram section.
- Explain Graph-RAG tradeoffs.
- Add streaming + feedback + guardrail docs.

## 4) Recommended implementation order (fastest path)

Phase A: Retrieval intelligence
1. `markdown_chunker.py`
2. `graph_store.py`
3. `entity_extractor.py`
4. `build_index.py` and `sync_index.py`
5. `graph_retriever.py`
6. `retriever.py` hybrid merge

Phase B: Agentic orchestration
1. `router.py`
2. `critic.py`
3. `orchestrator.py`
4. `llm_provider.py` + `groq_client.py`
5. `api/chat.py` orchestration integration

Phase C: UX and trust
1. `/chat/stream`
2. frontend streaming update
3. feedback endpoint + UI
4. transparency/evidence panel

Phase D: hardening
1. guardrails
2. eval expansion
3. telemetry + CI upgrades
4. README architecture and tradeoffs

## 5) Acceptance criteria for V2

1. Complex cross-domain query quality visibly improved over V1.
2. Every answer includes linked sources and claim evidence map.
3. OOD prompts are rejected politely with clear scope messaging.
4. Critic loop reduces unsupported claims before user delivery.
5. Streaming UI responds within first-token SLA (<1.5s target).
6. Evaluation script reports route accuracy + grounding metrics.

## 6) Current gap summary (from current codebase)

- Implemented already:
- FastAPI API, React UI, vector retrieval, incremental sync, tests, CI scaffolding.

- Missing for V2:
- graph store, routing agent, self-critique, stream API/UI, feedback loop, advanced guardrails, claim-level evidence mapping.

## 7) Suggested V2 branch strategy

1. Create branch `feat/v2-agentic-graph-rag`.
2. Land each phase as separate PRs:
- PR1 retrieval intelligence
- PR2 orchestration and multi-model support
- PR3 streaming + UX trust layer
- PR4 guardrails, evaluation, observability
3. Keep V1 endpoint compatibility during migration.
