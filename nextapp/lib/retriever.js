import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const DATA_DIR = process.env.DATA_DIR || join(process.cwd(), 'data');
const INDEX_PATH = join(DATA_DIR, 'vector_index.json');

// Module-level cache
let _index = null;

function loadIndex() {
  if (_index !== null) return _index;

  if (!existsSync(INDEX_PATH)) {
    console.warn(`[retriever] vector_index.json not found at ${INDEX_PATH}`);
    _index = [];
    return _index;
  }

  try {
    const raw = readFileSync(INDEX_PATH, 'utf-8');
    _index = JSON.parse(raw);
    console.log(`[retriever] Loaded ${_index.length} entries from ${INDEX_PATH}`);
  } catch (err) {
    console.error('[retriever] Failed to load index:', err);
    _index = [];
  }
  return _index;
}

function cosineSimilarity(a, b) {
  const len = Math.min(a.length, b.length);
  if (len === 0) return -1;
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < len; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  if (denom === 0) return -1;
  return dot / denom;
}

export function searchVector(queryEmbedding, topK = 4) {
  const index = loadIndex();
  if (!index.length) {
    return [{
      title: 'Index not built yet',
      url: 'https://handbook.gitlab.com',
      snippet: 'Run the index build script to populate vector_index.json.',
      section: 'General',
    }];
  }

  const scored = index.map((entry) => ({
    score: cosineSimilarity(queryEmbedding, entry.embedding),
    entry,
  }));

  scored.sort((a, b) => b.score - a.score);

  // Enforce URL diversity
  const seen = new Set();
  const selected = [];
  const overflow = [];

  for (const { entry } of scored) {
    if (!seen.has(entry.url)) {
      seen.add(entry.url);
      selected.push(entry);
    } else {
      overflow.push(entry);
    }
    if (selected.length >= topK * 2) break;
  }

  return [...selected, ...overflow].slice(0, topK).map((e) => ({
    title: e.title,
    url: e.url,
    snippet: e.snippet,
    section: e.section_path || e.section || 'General',
  }));
}

export function isIndexLoaded() {
  const index = loadIndex();
  return index.length > 0;
}
