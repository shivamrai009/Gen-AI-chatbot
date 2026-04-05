const OFF_TOPIC_TERMS = new Set([
  'python script',
  'write code',
  'weather',
  'movie',
  'football',
  'recipe',
  'crypto',
]);

const GRAPH_HINT_TERMS = new Set([
  'connect',
  'relationship',
  'impact',
  'between',
  'dependency',
  'tradeoff',
  'owner',
  'responsible',
]);

const VAGUE_PATTERNS = new Set([
  'tell me something',
  'tell me more',
  'tell me',
  'what do you know',
  'what can you tell',
  'just ask',
  "i don't know",
  'anything',
  'something',
  'go on',
  'keep going',
]);

/**
 * @param {string} question
 * @param {Array<{role: string, content: string}>} history
 * @returns {{ route: string, confidence: number, reason: string }}
 */
export function routeQuery(question, history = []) {
  const lowered = question.toLowerCase().trim();
  const words = lowered.split(/\s+/);

  // If history exists and question is short, treat as contextual reply
  if (history.length > 0 && words.length <= 4) {
    return { route: 'vector', confidence: 0.75, reason: 'Short contextual reply with active conversation history' };
  }

  // Short or vague
  if (words.length <= 2 || [...VAGUE_PATTERNS].some((p) => lowered.includes(p))) {
    return { route: 'clarify', confidence: 0.8, reason: 'Query too short or vague' };
  }

  // Off-topic
  if ([...OFF_TOPIC_TERMS].some((t) => lowered.includes(t))) {
    return { route: 'reject', confidence: 0.95, reason: 'Out-of-domain request' };
  }

  // Graph hints
  if ([...GRAPH_HINT_TERMS].some((t) => lowered.includes(t))) {
    return { route: 'hybrid', confidence: 0.8, reason: 'Likely relational question' };
  }

  return { route: 'vector', confidence: 0.65, reason: 'Default semantic retrieval' };
}
