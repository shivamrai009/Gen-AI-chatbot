const SECURITY_BLOCK_TERMS = new Set([
  'sql injection',
  'xss',
  'malware',
  'exploit',
  'ddos',
  'credential stuffing',
]);

const OFF_SCOPE_TERMS = new Set([
  'write code',
  'python script',
  'movie recommendation',
  'recipe',
  'crypto trading',
]);

const DOMAIN_TERMS = new Set([
  'gitlab',
  'handbook',
  'direction',
  'deployment',
  'marketing',
  'engineering',
  'strategy',
  'pipeline',
  'ci',
  'cd',
  'security',
  'product',
  'okr',
]);

function normalize(text) {
  return text.replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter((t) => t.length > 2);
}

/**
 * @param {string} question
 * @param {Array} history
 * @returns {{ blocked: boolean, reason: string, response?: string }}
 */
export function checkGuardrails(question, history = []) {
  const lowered = question.toLowerCase();

  if ([...SECURITY_BLOCK_TERMS].some((t) => lowered.includes(t))) {
    return {
      blocked: true,
      reason: 'security-policy-block',
      response:
        'I cannot help with harmful cybersecurity misuse requests. ' +
        'I can help with GitLab documentation, processes, and strategy topics.',
    };
  }

  if ([...OFF_SCOPE_TERMS].some((t) => lowered.includes(t))) {
    return {
      blocked: true,
      reason: 'off-scope-query',
      response:
        'I am scoped to GitLab Handbook and Direction knowledge. ' +
        'Please ask a GitLab process, team, or strategy question.',
    };
  }

  // Skip domain-ratio check for continuing conversations
  if (!history || history.length === 0) {
    const tokens = normalize(lowered);
    if (tokens.length > 4) {
      const domainHits = tokens.filter((t) => DOMAIN_TERMS.has(t)).length;
      const ratio = domainHits / tokens.length;
      if (ratio < 0.06) {
        return {
          blocked: true,
          reason: 'low-domain-relevance',
          response:
            "That looks outside this assistant's scope. " +
            'Try asking about GitLab handbook policies, direction, teams, or delivery strategy.',
        };
      }
    }
  }

  return { blocked: false, reason: 'allowed' };
}
