import { NextResponse } from 'next/server';
import { authenticateRequest } from '../../../../../lib/auth.js';
import { getConversation, updateConversationTitle } from '../../../../../lib/store.js';

export async function PATCH(request, { params }) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const { id } = await params;
    const conv = await getConversation(id);
    if (!conv) return NextResponse.json({ detail: 'Not found' }, { status: 404 });
    if (conv.username !== payload.username) return NextResponse.json({ detail: 'Forbidden' }, { status: 403 });

    const body = await request.json();
    const { title } = body;
    if (!title) return NextResponse.json({ detail: 'title is required' }, { status: 400 });

    await updateConversationTitle(id, title);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[title PATCH]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
