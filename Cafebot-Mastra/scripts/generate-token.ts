import { readFileSync } from 'node:fs';
import { createHmac } from 'node:crypto';

function readSecret(): string {
  const env = readFileSync('.env.development', 'utf8');
  const line = env.split(/\r?\n/).find((l) => l.startsWith('MASTRA_JWT_SECRET='));
  if (!line) throw new Error('MASTRA_JWT_SECRET no encontrado en .env.development');
  return line.slice('MASTRA_JWT_SECRET='.length).trim();
}

const b64url = (input: string | Buffer) => Buffer.from(input).toString('base64url');

// Firma un JWT HS256 sin dependencias externas.
function signJwt(payload: Record<string, unknown>, secret: string): string {
  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify(payload));
  const data = `${header}.${body}`;
  const signature = createHmac('sha256', secret).update(data).digest('base64url');
  return `${data}.${signature}`;
}

const sub = process.argv[2] ?? 'juan-carlos';
const token = signJwt({ sub, name: sub, iat: Math.floor(Date.now() / 1000) }, readSecret());
console.log(token);
