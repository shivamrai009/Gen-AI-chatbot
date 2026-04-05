# Deployment Guide

Architecture: **Frontend → Vercel** · **Backend → Render (Docker)**

---

## 1 — Deploy the Backend to Render

### One-time setup

1. Push this repo to GitHub (the `render.yaml` auto-configures the service)
2. Go to [render.com](https://render.com) → New → **Blueprint**
3. Connect your GitHub repo — Render reads `render.yaml` automatically

### Environment variables to set in the Render dashboard

After the service is created, go to **Environment** and add:

| Variable | Value |
|---|---|
| `GEMINI_API_KEY` | Your key from [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `GROQ_API_KEY` | Your key from [console.groq.com](https://console.groq.com/keys) (optional fallback) |
| `JWT_SECRET` | Run `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALLOWED_ORIGINS` | Your Vercel frontend URL, e.g. `https://your-app.vercel.app` |

Everything else is pre-configured in `render.yaml`.

### Notes
- Free tier services **spin down after 15 min of inactivity** (first request after sleep is slow ~30s)
- Free tier has **ephemeral storage** — chat history and user accounts reset on restart
- Upgrade to the **Starter plan ($7/mo)** and uncomment the `disk:` block in `render.yaml` to persist data

---

## 2 — Deploy the Frontend to Vercel

### One-time setup

1. Go to [vercel.com](https://vercel.com) → New Project → Import your GitHub repo
2. Set **Root Directory** to `frontend`
3. Framework will auto-detect as **Vite**
4. Click Deploy

### Environment variables to set in Vercel dashboard

Go to **Project → Settings → Environment Variables**:

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | Your Render backend URL, e.g. `https://gitlab-ai-backend.onrender.com` |

### Notes
- Every push to `main` triggers an automatic redeploy
- The `frontend/vercel.json` handles SPA routing (so `/chat` doesn't 404 on refresh)
- **Do not** set `VITE_API_BASE_URL` for Preview deployments if you want them to use a separate backend

---

## 3 — Local Development

```bash
# Backend
cd backend
cp .env.example .env          # fill in your API keys
python -m uvicorn app.main:app --reload --port 8000
# OR from repo root:
python run.py --reload

# Frontend (in a new terminal)
cd frontend
cp .env.example .env.local    # leave VITE_API_BASE_URL empty for dev proxy
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies all API calls to http://localhost:8000.

---

## 4 — Rebuild the Knowledge Index

The vector index (`data/vector_index.json`) and knowledge graph (`data/knowledge_graph.json`)
are committed to the repo and baked into the Docker image. To rebuild them:

```bash
cd /repo-root
pip install -r backend/requirements.txt
python scripts/build_index.py
```

Then commit and push — Render will rebuild the Docker image automatically.

---

## 5 — Repository Structure

```
.
├── backend/                  # FastAPI backend (deployed to Render)
│   ├── app/                  # Application code
│   ├── data/
│   │   ├── vector_index.json     # Pre-built vector embeddings (committed)
│   │   └── knowledge_graph.json  # Knowledge graph (committed)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # React/Vite frontend (deployed to Vercel)
│   ├── src/
│   ├── vercel.json
│   ├── package.json
│   └── .env.example
├── scripts/                  # Index builder and eval scripts
├── render.yaml               # Render Blueprint config (backend)
└── run.py                    # Local dev shortcut: python run.py
```
