import { NextResponse } from 'next/server';
import { authenticateRequest } from '../../../lib/auth.js';
import { createConversation, listConversations } from '../../../lib/store.js';

export async function GET(request) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const convs = await listConversations(payload.username);
    return NextResponse.json(convs);
  } catch (err) {
    console.error('[conversations GET]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}

export async function POST(request) {
  const payload = await authenticateRequest(request);
  if (!payload) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });

  try {
    const body = await request.json();
    const title = body.title || 'New conversation';
    const conv = await createConversation(payload.username, title);
    return NextResponse.json({
      id: conv.id,
      title: conv.title,
      created_at: new Date(Number(conv.createdAt)).toISOString(),
      updated_at: new Date(Number(conv.updatedAt)).toISOString(),
    }, { status: 201 });
  } catch (err) {
    console.error('[conversations POST]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
