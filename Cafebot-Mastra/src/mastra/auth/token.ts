import { createHmac } from 'node:crypto';

const b64url = (input: string | Buffer) => Buffer.from(input).toString('base64url');

// Firma un JWT HS256 (mismo algoritmo que valida MastraJwtAuth).
export function signJwt(payload: Record<string, unknown>, secret: string): string {
  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify(payload));
  const data = `${header}.${body}`;
  const signature = createHmac('sha256', secret).update(data).digest('base64url');
  return `${data}.${signature}`;
}
