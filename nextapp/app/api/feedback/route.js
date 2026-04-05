import { NextResponse } from 'next/server';
import { authenticateRequest } from '../../../lib/auth.js';
import { saveFeedback } from '../../../lib/store.js';

export async function POST(request) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const body = await request.json();
    const { trace_id, vote, comment } = body;

    if (!trace_id || !vote) {
      return NextResponse.json({ detail: 'trace_id and vote are required' }, { status: 400 });
    }

    await saveFeedback(trace_id, vote, comment || '');
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[feedback POST]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
