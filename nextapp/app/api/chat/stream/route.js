import { authenticateRequest } from '../../../../lib/auth.js';
import { orchestrate } from '../../../../lib/orchestrator.js';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function sseEvent(event, data) {
  if (event === 'message') {
    return `data: ${data}\n\n`;
  }
  return `event: ${event}\ndata: ${data}\n\n`;
}

export async function POST(request) {
  // Auth check
  const payload = await authenticateRequest(request);
  if (!payload) {
    return new Response(JSON.stringify({ detail: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ detail: 'Invalid JSON body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const { question, history = [] } = body;

  if (!question || typeof question !== 'string') {
    return new Response(JSON.stringify({ detail: 'question is required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      function send(event, data) {
        controller.enqueue(encoder.encode(sseEvent(event, data)));
      }

      try {
        const result = await orchestrate(question, history);

        // Stream the answer token by token (word by word)
        const words = result.answer.split(' ');
        for (let i = 0; i < words.length; i++) {
          const token = i < words.length - 1 ? words[i] + ' ' : words[i];
          // Escape newlines in tokens
          const escaped = token.replace(/\n/g, '\\n');
          send('message', escaped);
          // Small delay to simulate streaming
          await new Promise((r) => setTimeout(r, 5));
        }

        // Send metadata
        send('meta', `${result.model}|${result.route}|${result.traceId}|${result.criticPassed}`);

        // Send sources
        if (result.sources && result.sources.length > 0) {
          send('sources', JSON.stringify(result.sources));
        }

        // Send follow-ups
        if (result.followups && result.followups.length > 0) {
          send('followups', JSON.stringify(result.followups));
        }

        // Done
        send('done', '[DONE]');
      } catch (err) {
        console.error('[chat/stream]', err);
        send('error', err.message || 'Internal server error');
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
