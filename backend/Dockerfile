FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# curl is needed for the HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Copy pre-built knowledge index (committed to the repo).
# Baked into the image at build time so the app works immediately.
# To rebuild: cd /repo && python scripts/build_index.py
COPY data/vector_index.json    ./data/vector_index.json
COPY data/knowledge_graph.json ./data/knowledge_graph.json

# Create data dir for runtime files (chats.db, users.json).
# On Render free tier these reset on restart — add a persistent disk
# in render.yaml to preserve them across deploys.
RUN mkdir -p data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
