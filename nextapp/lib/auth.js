import { SignJWT, jwtVerify } from 'jose';
import bcrypt from 'bcryptjs';

const JWT_SECRET = process.env.JWT_SECRET || 'gitlab-ai-dev-secret-change-in-production-32chars';
const secret = new TextEncoder().encode(JWT_SECRET);

export async function hashPassword(password) {
  return bcrypt.hash(password, 10);
}

export async function verifyPassword(password, hash) {
  return bcrypt.compare(password, hash);
}

export async function signToken(payload) {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('7d')
    .sign(secret);
}

export async function verifyToken(token) {
  try {
    const { payload } = await jwtVerify(token, secret);
    return payload;
  } catch {
    return null;
  }
}

export function extractBearerToken(request) {
  const auth = request.headers.get('authorization') || '';
  if (auth.startsWith('Bearer ')) return auth.slice(7);
  return null;
}

export async function authenticateRequest(request) {
  const token = extractBearerToken(request);
  if (!token) return null;
  return verifyToken(token);
}
