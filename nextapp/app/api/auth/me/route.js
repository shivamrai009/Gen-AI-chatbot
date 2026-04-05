import { NextResponse } from 'next/server';
import { authenticateRequest } from '../../../../lib/auth.js';
import { getUserByUsername } from '../../../../lib/store.js';

export async function GET(request) {
  try {
    const payload = await authenticateRequest(request);
    if (!payload) {
      return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 });
    }

    const user = await getUserByUsername(payload.username);
    if (!user) {
      return NextResponse.json({ detail: 'User not found' }, { status: 404 });
    }

    return NextResponse.json({ username: user.username, email: user.email });
  } catch (err) {
    console.error('[auth/me]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
