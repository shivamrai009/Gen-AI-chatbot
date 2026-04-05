import { NextResponse } from 'next/server';
import { verifyPassword, signToken } from '../../../../lib/auth.js';
import { getUserByUsername } from '../../../../lib/store.js';

export async function POST(request) {
  try {
    let username, password;

    const contentType = request.headers.get('content-type') || '';

    if (contentType.includes('application/x-www-form-urlencoded')) {
      const text = await request.text();
      const params = new URLSearchParams(text);
      username = params.get('username');
      password = params.get('password');
    } else {
      // JSON body
      const body = await request.json();
      username = body.username;
      password = body.password;
    }

    if (!username || !password) {
      return NextResponse.json({ detail: 'username and password are required' }, { status: 400 });
    }

    const user = await getUserByUsername(username);
    if (!user) {
      return NextResponse.json({ detail: 'Invalid username or password' }, { status: 401 });
    }

    const valid = await verifyPassword(password, user.passwordHash);
    if (!valid) {
      return NextResponse.json({ detail: 'Invalid username or password' }, { status: 401 });
    }

    const token = await signToken({ username: user.username, email: user.email });
    return NextResponse.json({ access_token: token, username: user.username });
  } catch (err) {
    console.error('[auth/login]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
