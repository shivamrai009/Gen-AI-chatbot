/**
 * KV store abstraction.
 * Uses @vercel/kv when KV_REST_API_URL is set, otherwise falls back to an
 * in-memory Map so the app works locally without any external dependencies.
 */

let kv = null;

async function getKV() {
  if (kv) return kv;

  if (process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN) {
    const { kv: vercelKv } = await import('@vercel/kv');
    kv = vercelKv;
    return kv;
  }

  // In-memory fallback
  kv = new InMemoryKV();
  return kv;
}

// ─── In-memory KV implementation ───────────────────────────────────────────

class InMemoryKV {
  constructor() {
    this._store = new Map();
    this._zsets = new Map(); // sorted sets: key -> Map<member, score>
    this._lists = new Map(); // lists: key -> Array<string>
  }

  async hset(key, data) {
    const existing = this._store.get(key) || {};
    this._store.set(key, { ...existing, ...data });
    return Object.keys(data).length;
  }

  async hgetall(key) {
    return this._store.get(key) || null;
  }

  async set(key, value) {
    this._store.set(key, value);
    return 'OK';
  }

  async get(key) {
    return this._store.get(key) ?? null;
  }

  async del(key) {
    this._store.delete(key);
    this._zsets.delete(key);
    this._lists.delete(key);
    return 1;
  }

  async zadd(key, ...args) {
    if (!this._zsets.has(key)) this._zsets.set(key, new Map());
    const zset = this._zsets.get(key);
    let added = 0;
    for (const arg of args) {
      if (arg && typeof arg === 'object' && 'score' in arg && 'member' in arg) {
        if (!zset.has(arg.member)) added++;
        zset.set(arg.member, arg.score);
      }
    }
    return added;
  }

  async zrange(key, start, stop, opts = {}) {
    const zset = this._zsets.get(key);
    if (!zset) return [];
    // Sort by score desc for REV, asc otherwise
    const sorted = [...zset.entries()].sort((a, b) =>
      opts.rev ? b[1] - a[1] : a[1] - b[1]
    );
    const sliced = sorted.slice(start, stop === -1 ? undefined : stop + 1);
    return sliced.map(([member]) => member);
  }

  async zrem(key, member) {
    const zset = this._zsets.get(key);
    if (!zset) return 0;
    const existed = zset.has(member);
    zset.delete(member);
    return existed ? 1 : 0;
  }

  async rpush(key, ...values) {
    if (!this._lists.has(key)) this._lists.set(key, []);
    const list = this._lists.get(key);
    list.push(...values);
    return list.length;
  }

  async lrange(key, start, stop) {
    const list = this._lists.get(key);
    if (!list) return [];
    return list.slice(start, stop === -1 ? undefined : stop + 1);
  }
}

// ─── Public API ──────────────────────────────────────────────────────────────

export async function createUser(username, email, passwordHash) {
  const store = await getKV();
  const userData = { username, email, passwordHash, createdAt: Date.now() };
  await store.hset(`user:${username}`, userData);
  await store.set(`email:${email}`, username);
  return userData;
}

export async function getUserByUsername(username) {
  const store = await getKV();
  return store.hgetall(`user:${username}`);
}

export async function getUserByEmail(email) {
  const store = await getKV();
  const username = await store.get(`email:${email}`);
  if (!username) return null;
  return store.hgetall(`user:${username}`);
}

export async function createConversation(username, title) {
  const { v4: uuidv4 } = await import('uuid');
  const store = await getKV();
  const id = uuidv4();
  const now = Date.now();
  const conv = { id, username, title, createdAt: now, updatedAt: now };
  await store.hset(`conv:${id}`, conv);
  await store.zadd(`convs:${username}`, { score: now, member: id });
  return conv;
}

export async function getConversation(id) {
  const store = await getKV();
  return store.hgetall(`conv:${id}`);
}

export async function listConversations(username) {
  const store = await getKV();
  const ids = await store.zrange(`convs:${username}`, 0, -1, { rev: true });
  const convs = await Promise.all(ids.map((id) => store.hgetall(`conv:${id}`)));
  return convs.filter(Boolean).map((c) => ({
    id: c.id,
    title: c.title,
    created_at: new Date(Number(c.createdAt)).toISOString(),
    updated_at: new Date(Number(c.updatedAt)).toISOString(),
  }));
}

export async function updateConversationTitle(id, title) {
  const store = await getKV();
  const existing = await store.hgetall(`conv:${id}`);
  if (!existing) return null;
  await store.hset(`conv:${id}`, { title, updatedAt: Date.now() });
  return { status: 'ok' };
}

export async function deleteConversation(id, username) {
  const store = await getKV();
  await store.del(`conv:${id}`);
  await store.del(`msgs:${id}`);
  await store.zrem(`convs:${username}`, id);
}

export async function addMessage(convId, role, content, sources = [], route = null, traceId = null) {
  const { v4: uuidv4 } = await import('uuid');
  const store = await getKV();
  const msg = {
    id: uuidv4(),
    convId,
    role,
    content,
    sources: JSON.stringify(sources || []),
    route: route || null,
    trace_id: traceId || null,
    createdAt: Date.now(),
  };
  await store.rpush(`msgs:${convId}`, JSON.stringify(msg));
  await store.hset(`conv:${convId}`, { updatedAt: Date.now() });
  return msg;
}

export async function getMessages(convId) {
  const store = await getKV();
  const raw = await store.lrange(`msgs:${convId}`, 0, -1);
  return raw.map((item) => {
    const msg = JSON.parse(item);
    return {
      ...msg,
      sources: msg.sources ? JSON.parse(msg.sources) : [],
    };
  });
}

export async function saveFeedback(traceId, vote, comment) {
  const store = await getKV();
  const { v4: uuidv4 } = await import('uuid');
  const id = uuidv4();
  await store.hset(`feedback:${id}`, { traceId, vote, comment: comment || '', createdAt: Date.now() });
  return { status: 'ok' };
}
