# GitLab AI Chatbot

A GenAI chatbot that lets GitLab employees and candidates explore the [GitLab Handbook](https://handbook.gitlab.com) and [Direction](https://about.gitlab.com/direction/) through a conversational interface. Built with Next.js (App Router) on Vercel and powered by Gemini 2.0 Flash.

**Live demo:** _(add your Vercel URL here)_

---

## Features

- **Hybrid RAG** — vector similarity search + knowledge graph entity retrieval, merged and ranked
- **Streaming answers** — server-sent events (SSE), tokens appear word-by-word
- **Agentic pipeline** — query router → retrieval → answer generation → AI critic → follow-ups
- **Guardrails** — blocks off-scope and harmful queries before they reach the LLM
- **AI Critic** — lexical grounding check with one automatic retry on weak answers
- **Follow-up chips** — 3 contextual follow-up questions generated per answer
- **Source citations** — every answer links back to the handbook/direction pages used
- **Authentication** — JWT-based register/login with bcrypt password hashing
- **Chat history** — conversations persisted in Vercel KV (Upstash Redis); in-memory fallback for local dev
- **Light/dark theme** — system-preference aware with flash-free toggle
- **Markdown rendering** — full GFM support (tables, code blocks, lists) in chat bubbles
- **Feedback** — thumbs up/down per answer stored for later analysis
- **Telemetry** — structured per-request trace logs (route, retrieval, generation, critic stages)
- **Evaluation** — `scripts/evaluate.py` reports citation coverage, keyword adequacy, route accuracy, guardrail handling, critic pass rate

---

## Architecture

```
User browser
    │  SSE (text/event-stream)
    ▼
Next.js App Router (Vercel)
    ├── app/api/chat/stream      — orchestration entry point
    ├── app/api/auth/*           — register / login / me
    ├── app/api/conversations/*  — CRUD + message history
    └── app/api/feedback         — thumbs up/down

    lib/orchestrator.js
        1. checkGuardrails()     — block harmful / off-scope
        2. routeQuery()          — clarify / reject / vector / hybrid
        3. embedText()           — Gemini embedding-001 (3072-dim)
        4. searchVector()        — cosine similarity over local JSON index
        5. generateAnswer()      — Gemini 2.0 Flash with full history
        6. evaluateCritic()      — lexical overlap grounding check
        7. generateFollowups()   — 3 follow-up questions (Groq fallback)

Vercel KV (Upstash Redis)        — user accounts, conversations, messages
data/vector_index.json           — 3072-dim embeddings (committed to repo)
data/knowledge_graph.json        — entity relationship graph (committed)
```

---

## Quick start — local development

### Prerequisites

- Node.js 20+
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)

### 1. Install dependencies

```bash
cd nextapp
npm install
```

### 2. Configure environment variables

```bash
cp .env.example .env.local
# Edit .env.local and fill in your keys (see table below)
```

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini API key for generation + embeddings |
| `JWT_SECRET` | Yes (prod) | 32+ char secret for JWT signing. Dev default is insecure. |
| `KV_REST_API_URL` | No | Vercel KV URL — omit to use in-memory storage locally |
| `KV_REST_API_TOKEN` | No | Vercel KV token |
| `GROQ_API_KEY` | No | Groq key for follow-up fallback (llama-3.1-8b-instant) |

### 3. Run the dev server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Deploy to Vercel (recommended)

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import repo
3. Set **Root Directory** to `nextapp`
4. Framework auto-detects as **Next.js**
5. Add environment variables in **Project → Settings → Environment Variables**:
   - `GEMINI_API_KEY`
   - `JWT_SECRET` (generate with: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"`)
   - `KV_REST_API_URL` + `KV_REST_API_TOKEN` (from a Vercel KV database — see [Vercel KV docs](https://vercel.com/docs/storage/vercel-kv))
   - `GROQ_API_KEY` (optional)
6. Click **Deploy**

Every push to `main` triggers an automatic redeploy.

---

## Rebuilding the knowledge index

The vector index (`data/vector_index.json`) and knowledge graph (`data/knowledge_graph.json`) are committed to the repo and copied into `nextapp/data/` — they load directly from disk with no external DB needed.

To rebuild from the latest GitLab Handbook and Direction pages:

```bash
# From repo root (requires Python 3.10+ and a virtual env)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Full rebuild (~20 min, ~44 MB output)
python scripts/build_index.py

# Incremental sync (only changed pages)
python scripts/sync_index.py

# Copy updated index into the Next.js app
cp backend/data/vector_index.json nextapp/data/
cp backend/data/knowledge_graph.json nextapp/data/
```

Then commit and push — Vercel will redeploy automatically.

---

## Running evaluation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python ../scripts/evaluate.py
```

Reports: citation coverage, keyword adequacy, route accuracy, guardrail handling, critic pass rate.

---

## Repository structure

```
.
├── nextapp/                  # Next.js app — deploy this to Vercel
│   ├── app/
│   │   ├── api/              # Route Handlers (chat, auth, conversations, feedback)
│   │   ├── chat/             # Chat UI page
│   │   ├── login/            # Login page
│   │   ├── register/         # Register page
│   │   └── page.jsx          # Landing page
│   ├── components/           # ThemeProvider
│   ├── lib/                  # Core pipeline (orchestrator, retriever, gemini, router, ...)
│   ├── data/                 # vector_index.json + knowledge_graph.json (committed)
│   └── .env.example
├── backend/                  # Python FastAPI backend (reference / index building)
│   ├── app/                  # API + services (guardrails, router, critic, orchestrator)
│   ├── data/                 # Source of truth for index files
│   └── requirements.txt
├── scripts/                  # build_index.py, sync_index.py, evaluate.py
├── frontend/                 # Legacy React/Vite frontend (superseded by nextapp/)
├── DEPLOY.md                 # Detailed deployment guide
└── run.py                    # Quick backend launcher: python run.py
```

---

## API reference (Next.js routes)

### Health

```
GET /api/health
→ { status: "ok", timestamp: "..." }
```

### Auth

```
POST /api/auth/register   { username, password }  → { token, user }
POST /api/auth/login      { username, password }  → { token, user }
GET  /api/auth/me                                  → { user }   (requires Bearer token)
```

### Chat

```
POST /api/chat/stream
Authorization: Bearer <token>
{ question: "...", history: [{role, content}, ...] }

→ text/event-stream
  event: message    data: <token>
  event: meta       data: <model>|<route>|<traceId>|<criticPassed>
  event: sources    data: [{title, url, snippet}, ...]
  event: followups  data: ["...", "...", "..."]
  event: done       data: [DONE]
  event: error      data: <message>
```

### Conversations

```
GET    /api/conversations          → list user's conversations
POST   /api/conversations          → create conversation
GET    /api/conversations/:id      → get conversation
DELETE /api/conversations/:id      → delete conversation
GET    /api/conversations/:id/messages   → list messages
POST   /api/conversations/:id/messages   → add message
PATCH  /api/conversations/:id/title      → update title
```

### Feedback

```
POST /api/feedback   { traceId, vote: "up"|"down", comment? }
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| LLM | Gemini 2.0 Flash (`gemini-2.0-flash`) |
| Embeddings | Gemini Embedding-001 (3072 dimensions) |
| Fallback LLM | Groq — Llama 3.1 8B Instant |
| Auth | jose (JWT HS256) + bcryptjs |
| Storage | Vercel KV (Upstash Redis) / in-memory fallback |
| Retrieval | Local JSON vector index (cosine similarity) + knowledge graph |
| Streaming | Server-Sent Events (ReadableStream) |
| UI | React 19, CSS custom properties (dual theme) |
| Markdown | react-markdown + remark-gfm |
| Deployment | Vercel |
