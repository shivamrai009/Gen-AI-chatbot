const GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models';
const GEMINI_MODEL = 'gemini-2.0-flash';
const GROQ_API_BASE = 'https://api.groq.com/openai/v1/chat/completions';
const GROQ_MODEL = 'llama-3.1-8b-instant';

function buildPrompt(question, sources) {
  const formatted = sources
    .map((s) => `Source: ${s.title}\nURL: ${s.url}\nSnippet: ${s.snippet}`)
    .join('\n\n');

  return (
    'You are a helpful assistant for GitLab handbook and direction questions. ' +
    'Only answer using the provided source snippets. If the context is insufficient, ' +
    'say what is missing and suggest where to look.\n\n' +
    `Question:\n${question}\n\n` +
    `Context:\n${formatted}`
  );
}

function extractGeminiText(data) {
  try {
    return data.candidates[0].content.parts[0].text;
  } catch {
    return 'I could not generate a reliable answer from the current context.';
  }
}

async function callGemini(contents) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) return null;

  const endpoint = `${GEMINI_API_BASE}/${GEMINI_MODEL}:generateContent?key=${key}`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contents }),
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Gemini HTTP ${res.status}: ${msg}`);
  }

  return res.json();
}

async function callGroq(messages) {
  const key = process.env.GROQ_API_KEY;
  if (!key) return null;

  const res = await fetch(GROQ_API_BASE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      messages,
      temperature: 0.2,
    }),
  });

  if (!res.ok) return null;

  try {
    const data = await res.json();
    return data.choices?.[0]?.message?.content?.trim() || null;
  } catch {
    return null;
  }
}

export async function generateAnswer(question, sources, history = []) {
  const prompt = buildPrompt(question, sources);

  // Build Gemini multi-turn contents
  const contents = [];
  for (const turn of history) {
    const role = turn.role === 'assistant' ? 'model' : 'user';
    contents.push({ role, parts: [{ text: turn.content }] });
  }
  contents.push({ role: 'user', parts: [{ text: prompt }] });

  // Try Gemini
  if (process.env.GEMINI_API_KEY) {
    let backoff = 1000;
    for (let attempt = 0; attempt <= 2; attempt++) {
      try {
        const data = await callGemini(contents);
        if (data) return extractGeminiText(data);
      } catch (err) {
        if (attempt < 2) {
          await new Promise((r) => setTimeout(r, backoff));
          backoff *= 2;
          continue;
        }
        console.error('[gemini] generateAnswer failed after retries:', err.message);
      }
    }
  }

  // Groq fallback
  const messages = [
    { role: 'system', content: 'You are a helpful assistant focused on GitLab handbook and direction knowledge.' },
    ...history.map((h) => ({ role: h.role, content: h.content })),
    { role: 'user', content: prompt },
  ];
  const groqAnswer = await callGroq(messages);
  if (groqAnswer) return groqAnswer;

  // Static fallback
  const sourceList = sources.map((s) => s.title).join(', ');
  return `Gemini API key is not configured. Question received: '${question}'. Relevant starting sources: ${sourceList}.`;
}

export async function embedText(text) {
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new Error('GEMINI_API_KEY not set');

  const endpoint = `${GEMINI_API_BASE}/gemini-embedding-001:embedContent?key=${key}`;
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'models/gemini-embedding-001',
      content: { parts: [{ text }] },
    }),
  });

  if (!res.ok) {
    const msg = await res.text();
    throw new Error(`Embed HTTP ${res.status}: ${msg}`);
  }

  const data = await res.json();
  return data.embedding.values;
}

function parseFollowups(text) {
  text = text.trim();
  // Try direct parse
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed.filter((q) => typeof q === 'string').slice(0, 3);
  } catch {}

  // Strip code fences
  const stripped = text.replace(/^```(?:json)?\s*/m, '').replace(/\s*```$/m, '').trim();
  try {
    const parsed = JSON.parse(stripped);
    if (Array.isArray(parsed)) return parsed.filter((q) => typeof q === 'string').slice(0, 3);
  } catch {}

  // Extract array from anywhere in text
  const match = text.match(/\[[\s\S]*?\]/);
  if (match) {
    try {
      const parsed = JSON.parse(match[0]);
      if (Array.isArray(parsed)) return parsed.filter((q) => typeof q === 'string').slice(0, 3);
    } catch {}
  }

  return [];
}

export async function generateFollowups(question, answer) {
  const prompt =
    'Given this Q&A about GitLab, suggest exactly 3 short follow-up questions ' +
    'a user might ask next. Return ONLY a valid JSON array of 3 strings, ' +
    'no explanation, no markdown code fences, no numbering.\n\n' +
    `Q: ${question}\nA: ${answer.slice(0, 600)}\n\n` +
    'Example output: ["What is X?", "How does Y work?", "Where can I find Z?"]';

  // Try Gemini
  if (process.env.GEMINI_API_KEY) {
    try {
      const data = await callGemini([{ role: 'user', parts: [{ text: prompt }] }]);
      if (data) {
        const text = extractGeminiText(data);
        const questions = parseFollowups(text);
        if (questions.length) return questions;
      }
    } catch (err) {
      console.error('[gemini] generateFollowups Gemini failed:', err.message);
    }
  }

  // Groq fallback
  if (process.env.GROQ_API_KEY) {
    try {
      const result = await callGroq([
        { role: 'system', content: 'You are a helpful assistant. Return only valid JSON arrays.' },
        { role: 'user', content: prompt },
      ]);
      if (result) {
        const questions = parseFollowups(result);
        if (questions.length) return questions;
      }
    } catch (err) {
      console.error('[gemini] generateFollowups Groq failed:', err.message);
    }
  }

  return [];
}
