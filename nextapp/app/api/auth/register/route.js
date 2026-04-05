import { NextResponse } from 'next/server';
import { hashPassword, signToken } from '../../../../lib/auth.js';
import { createUser, getUserByUsername, getUserByEmail } from '../../../../lib/store.js';

export async function POST(request) {
  try {
    const body = await request.json();
    const { username, email, password } = body;

    if (!username || !email || !password) {
      return NextResponse.json({ detail: 'username, email, and password are required' }, { status: 400 });
    }

    if (username.length < 3) {
      return NextResponse.json({ detail: 'Username must be at least 3 characters' }, { status: 400 });
    }

    if (password.length < 6) {
      return NextResponse.json({ detail: 'Password must be at least 6 characters' }, { status: 400 });
    }

    const existing = await getUserByUsername(username);
    if (existing) {
      return NextResponse.json({ detail: 'Username already taken' }, { status: 400 });
    }

    const existingEmail = await getUserByEmail(email);
    if (existingEmail) {
      return NextResponse.json({ detail: 'Email already registered' }, { status: 400 });
    }

    const passwordHash = await hashPassword(password);
    await createUser(username, email, passwordHash);

    const token = await signToken({ username, email });
    return NextResponse.json({ access_token: token, username }, { status: 201 });
  } catch (err) {
    console.error('[auth/register]', err);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
