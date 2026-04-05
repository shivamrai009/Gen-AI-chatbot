import { NextResponse } from 'next/server';
import { authenticateRequest } from '../../../../../lib/auth.js';
import { getConversation, addMessage, getMessages } from '../../../../../lib/store.js';

export async function GET(request, { params }) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const { id } = await params;
    const conv = await getConversation(id);
    if (!conv) return NextResponse.json({ detail: 'Not found' }, { status: 404 });
    if (conv.username !== payload.username) return NextResponse.json({ detail: 'Forbidden' }, { status: 403 });

    const messages = await getMessages(id);
    return NextResponse.json(messages);
  } catch (err) {
    console.error('[messages GET]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(request, { params }) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const { id } = await params;
    const conv = await getConversation(id);
    if (!conv) return NextResponse.json({ detail: 'Not found' }, { status: 404 });
    if (conv.username !== payload.username) return NextResponse.json({ detail: 'Forbidden' }, { status: 403 });

    const body = await request.json();
    const { role, content, sources, route, trace_id } = body;

    if (!role || !content) {
      return NextResponse.json({ detail: 'role and content are required' }, { status: 400 });
    }

    const msg = await addMessage(id, role, content, sources || [], route || null, trace_id || null);
    return NextResponse.json({
      ...msg,
      sources: msg.sources || [],
    }, { status: 201 });
  } catch (err) {
    console.error('[messages POST]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
