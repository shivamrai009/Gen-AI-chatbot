function normalize(text) {
  return text
    .replace(/[^a-z0-9\s]/g, ' ')
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length > 2);
}

/**
 * @param {string} answer
 * @param {Array<{title: string, snippet: string}>} sources
 * @returns {{ passed: boolean, reason: string }}
 */
export function evaluateCritic(answer, sources) {
  if (!answer.trim()) {
    return { passed: false, reason: 'Empty answer' };
  }

  if (answer.toLowerCase().includes('api key is not configured')) {
    return { passed: true, reason: 'Fallback mode' };
  }

  if (!sources || sources.length === 0) {
    return { passed: false, reason: 'No retrieved sources' };
  }

  const answerTerms = new Set(normalize(answer));
  const sourceTerms = new Set();
  for (const s of sources) {
    for (const t of normalize(s.snippet || '')) sourceTerms.add(t);
    for (const t of normalize(s.title || '')) sourceTerms.add(t);
  }

  if (answerTerms.size === 0) {
    return { passed: false, reason: 'Answer has no lexical signal' };
  }

  let overlap = 0;
  for (const t of answerTerms) {
    if (sourceTerms.has(t)) overlap++;
  }

  const ratio = overlap / answerTerms.size;
  if (ratio < 0.08) {
    return { passed: false, reason: 'Low grounding overlap' };
  }

  return { passed: true, reason: 'Grounded by retrieved evidence' };
}
