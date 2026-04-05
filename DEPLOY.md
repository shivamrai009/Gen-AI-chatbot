# Deployment Guide

Architecture: **Next.js app → Vercel** (single platform, no separate backend needed)

---

## 1 — Deploy to Vercel

### One-time setup

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → New Project → Import your GitHub repo
3. Set **Root Directory** to `nextapp`
4. Framework auto-detects as **Next.js**
5. Click **Deploy**

### Environment variables to set in Vercel dashboard

Go to **Project → Settings → Environment Variables**:

| Variable | Required | Value |
|---|---|---|
| `GEMINI_API_KEY` | Yes | From [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `JWT_SECRET` | Yes | Run: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"` |
| `KV_REST_API_URL` | Recommended | From a Vercel KV database (see below) |
| `KV_REST_API_TOKEN` | Recommended | From the same Vercel KV database |
| `GROQ_API_KEY` | No | From [console.groq.com](https://console.groq.com/keys) — follow-up fallback |

### Setting up Vercel KV (persistent chat history)

1. In your Vercel project → **Storage** → **Create Database** → **KV**
2. Connect the KV database to your project
3. Vercel automatically injects `KV_REST_API_URL` and `KV_REST_API_TOKEN`

Without KV, the app uses an in-memory store — data resets on every cold start.

### Notes
- Every push to `main` triggers an automatic redeploy
- The vector index (`nextapp/data/vector_index.json`) is committed to the repo — no separate data pipeline needed on Vercel

---

## 2 — Local Development

```bash
cd nextapp
cp .env.example .env.local    # fill in at minimum GEMINI_API_KEY
npm install
npm run dev
```

Open http://localhost:3000.

Without `KV_REST_API_URL` set, the app uses in-memory storage — perfectly fine for local testing.

---

## 3 — Rebuild the Knowledge Index

The vector index and knowledge graph are committed to the repo at `nextapp/data/`. To rebuild from the latest GitLab Handbook:

```bash
# From repo root (requires Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

python scripts/build_index.py        # full rebuild (~20 min)
# OR
python scripts/sync_index.py         # incremental sync (changed pages only)

# Copy updated files into the Next.js app
cp backend/data/vector_index.json nextapp/data/
cp backend/data/knowledge_graph.json nextapp/data/
```

Then commit and push — Vercel redeploys automatically.

---

## 4 — Alternative: Backend + Separate Frontend (legacy)

The `backend/` (FastAPI) and `frontend/` (React/Vite) directories are the original architecture.
They still work but are superseded by the Next.js app. Use `render.yaml` to deploy the Python
backend to Render if needed (e.g. for the Python evaluation scripts in production).

---

## 5 — Repository Structure

```
.
├── nextapp/                  # Next.js app — deploy this to Vercel
│   ├── app/                  # Route Handlers + pages
│   ├── lib/                  # Core pipeline (orchestrator, retriever, gemini, ...)
│   ├── data/
│   │   ├── vector_index.json     # Pre-built embeddings (committed)
│   │   └── knowledge_graph.json  # Knowledge graph (committed)
│   ├── .env.example
│   └── package.json
├── backend/                  # FastAPI backend (index building + reference)
│   ├── app/
│   ├── data/                 # Source of truth for index files
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # Legacy React/Vite frontend (superseded)
├── scripts/                  # build_index.py, sync_index.py, evaluate.py
├── render.yaml               # Render Blueprint config (legacy backend)
└── run.py                    # Quick backend launcher: python run.py
```
