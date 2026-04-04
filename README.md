# Gen-AI-chatbot

GenAI chatbot for employees and aspiring employees to explore GitLab Handbook and Direction content through a simple conversational interface.

## Current implementation (starter MVP)

- FastAPI backend with:
- `POST /chat` endpoint
- Gemini API integration (with fallback mode if API key is missing)
- Health check endpoint `GET /health`
- Ingestion utilities for fetching and chunking page content
- Embedding-based local vector retrieval over indexed chunks
- Hierarchy-preserving section chunking and lightweight entity graph retrieval
- Incremental sync pipeline using checksum manifest
- React + Vite frontend with:
- Chat interface
- Suggested prompts
- Follow-up support
- Source links in responses

This is the first implementation slice with real retrieval. The chatbot now reads from a local embedding index generated from GitLab Handbook and Direction pages.

You can run retrieval in two modes:

- local: saves vectors in `backend/data/vector_index.json`
- postgres: stores vectors in Postgres with pgvector

## Core scripts

- `scripts/build_index.py`: full rebuild of the vector index from configured source URLs.
- `scripts/sync_index.py`: incremental sync (updates only changed pages and removes deleted sources).
- `scripts/seed_sources.py`: quick fetch/chunk sanity check.
- `scripts/evaluate.py`: lightweight quality evaluation over a fixed question set.

The retrieval path is now hybrid:

- vector similarity over indexed chunks
- entity graph retrieval over related concepts
- weighted merge of vector and graph evidence

Indexing now supports depth-limited internal link expansion from each seed URL so retrieval can use relevant subpages instead of only landing pages.

The chat pipeline now includes a lightweight agentic orchestrator:

- query router (`vector`, `graph`, `hybrid`, `clarify`, `reject`)
- retrieval execution by route
- answer generation
- critic pass to detect weak grounding and trigger one retry
- guardrails for off-scope and harmful-intent detection
- structured telemetry logs for route/retrieval/generation/critic stages

## Repository structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── models
│   │   └── services
│   └── requirements.txt
├── frontend
│   └── src
└── scripts
```

## Tech stack

- Backend: Python, FastAPI, httpx, BeautifulSoup
- Frontend: React, Vite
- LLM provider: Gemini API

## Local setup

Optional (from repository root):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For test dependencies from root:

```bash
pip install -r requirements-dev.txt
```

### 1) Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini key in `backend/.env`:

```env
GEMINI_API_KEY=your_key_here
```

Run backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2) Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open the app at `http://localhost:5173`.

## API quick reference

### Health

`GET /health`

Response:

```json
{
	"status": "ok",
	"timestamp": "2026-04-03T00:00:00Z"
}
```

### Chat

`POST /chat`

Request:

```json
{
	"question": "What is GitLab handbook-first culture?",
	"history": [
		{ "role": "user", "content": "Tell me about GitLab documentation" }
	]
}
```

Response:

```json
{
	"answer": "...",
	"sources": [
		{
			"title": "GitLab Handbook",
			"url": "https://handbook.gitlab.com",
			"snippet": "..."
		}
	],
	"model": "gemini-2.0-flash"
}
```

### Streaming chat

`POST /chat/stream`

Returns server-sent events with token chunks (`message`), metadata (`meta`), sources (`sources`), and completion (`done`).

### Feedback

`POST /feedback`

Request:

```json
{
	"trace_id": "<trace-id-from-chat-response>",
	"vote": "up",
	"comment": "Useful answer"
}
```

## Data ingestion bootstrap

Use the scripts below to bootstrap data:

```bash
cd backend
PYTHONPATH=. python ../scripts/seed_sources.py
```

Build the local vector index (required for retrieval):

```bash
cd backend
PYTHONPATH=. python ../scripts/build_index.py
```

To use pgvector instead of local JSON storage, set these values in `backend/.env`:

```env
VECTOR_BACKEND=postgres
POSTGRES_DSN=postgresql://user:password@host:5432/dbname
PGVECTOR_TABLE=knowledge_chunks
EMBEDDING_DIMENSIONS=768
```

Then run the same index build command. The script will auto-create the pgvector extension, table, and ANN index.

Useful crawl controls in `backend/.env`:

- `CRAWL_DEPTH` (default `1`)
- `MAX_CHILD_LINKS_PER_PAGE` (default `12`)
- `MAX_EXPANDED_PAGES_PER_SEED` (default `25`)

Run incremental sync:

```bash
cd backend
PYTHONPATH=. python ../scripts/sync_index.py
```

Run evaluation:

```bash
cd backend
PYTHONPATH=. python ../scripts/evaluate.py
```

Evaluation now reports:

- citation coverage
- keyword adequacy
- route accuracy
- guardrail handling
- critic pass rate

Telemetry output:

- runtime traces are written to `backend/data/telemetry.log`

## Testing

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

## CI and automation

- CI workflow: `.github/workflows/ci.yml`
- Scheduled index sync workflow: `.github/workflows/sync-index.yml`

Required repository secrets for scheduled sync:

- `GEMINI_API_KEY`
- `POSTGRES_DSN`

## Deployment

- Backend deployment scaffold:
- `backend/Dockerfile`
- `render.yaml`
- Frontend deployment scaffold:
- `frontend/vercel.json`

If `GEMINI_API_KEY` is not set, the indexer and retriever use deterministic fallback embeddings so local testing still works.

## Deployment targets (next step)

- Frontend: Vercel
- Backend: Render or Railway

## Next milestones

- Deploy public URL and document architecture/tradeoffs
- Add deeper prompt/guardrail evaluation and regression scoring
