import { NextResponse } from 'next/server';
import { authenticateRequest } from '../../../../lib/auth.js';
import { getConversation, deleteConversation } from '../../../../lib/store.js';

export async function DELETE(request, { params }) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const { id } = await params;
    const conv = await getConversation(id);
    if (!conv) return NextResponse.json({ detail: 'Not found' }, { status: 404 });
    if (conv.username !== payload.username) return NextResponse.json({ detail: 'Forbidden' }, { status: 403 });

    await deleteConversation(id, payload.username);
    return new NextResponse(null, { status: 204 });
  } catch (err) {
    console.error('[conversations DELETE]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
