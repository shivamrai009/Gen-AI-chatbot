import { checkGuardrails } from './guardrails.js';
import { routeQuery } from './router.js';
import { embedText, generateAnswer, generateFollowups } from './gemini.js';
import { searchVector } from './retriever.js';
import { evaluateCritic } from './critic.js';
import { v4 as uuidv4 } from 'uuid';

const TOP_K = 4;

/**
 * Run the full RAG pipeline and return a response object.
 * @param {string} question
 * @param {Array<{role: string, content: string}>} history
 * @returns {Promise<{answer, sources, route, traceId, criticPassed, followups, model}>}
 */
export async function orchestrate(question, history = []) {
  const traceId = uuidv4();
  const model = 'gemini-2.0-flash';

  // 1. Guardrails
  const guard = checkGuardrails(question, history);
  if (guard.blocked) {
    return {
      answer: guard.response || 'Request blocked by guardrails.',
      sources: [],
      route: 'reject',
      traceId,
      criticPassed: true,
      followups: [],
      model,
    };
  }

  // 2. Route
  const decision = routeQuery(question, history);

  if (decision.route === 'reject') {
    return {
      answer:
        'I can help with GitLab Handbook and Direction topics only. ' +
        'Please ask a question related to GitLab processes, strategy, teams, or documentation.',
      sources: [],
      route: decision.route,
      traceId,
      criticPassed: true,
      followups: [],
      model,
    };
  }

  if (decision.route === 'clarify') {
    return {
      answer:
        'Could you add a bit more detail so I can retrieve the right handbook or direction context? ' +
        'For example, include the team, process, or objective you mean.',
      sources: [],
      route: decision.route,
      traceId,
      criticPassed: true,
      followups: [],
      model,
    };
  }

  // 3. Build retrieval query
  let retrievalQuery = question;
  if (question.split(/\s+/).length <= 4 && history.length > 0) {
    const priorUserMsgs = history.filter((h) => h.role === 'user').map((h) => h.content);
    if (priorUserMsgs.length > 0) {
      retrievalQuery = `${priorUserMsgs[priorUserMsgs.length - 1]} ${question}`.trim();
    }
  }

  // 4. Retrieve sources via vector search
  let sources = [];
  try {
    const queryEmbedding = await embedText(retrievalQuery);
    sources = searchVector(queryEmbedding, TOP_K);
  } catch (err) {
    console.error('[orchestrator] Retrieval failed:', err.message);
    // Continue with empty sources (will likely fail critic but still respond)
  }

  // 5. Generate answer
  let answer = await generateAnswer(question, sources, history);

  // 6. Critic check with one retry
  let criticResult = evaluateCritic(answer, sources);
  if (!criticResult.passed) {
    const retryQuestion =
      'Answer strictly from the provided context and avoid unsupported claims. ' +
      `Original question: ${question}`;
    answer = await generateAnswer(retryQuestion, sources, history);
    criticResult = evaluateCritic(answer, sources);
  }

  // 7. Generate follow-ups
  let followups = [];
  try {
    followups = await generateFollowups(question, answer);
  } catch (err) {
    console.error('[orchestrator] Follow-ups failed:', err.message);
  }

  return {
    answer,
    sources,
    route: decision.route,
    traceId,
    criticPassed: criticResult.passed,
    followups,
    model,
  };
}
