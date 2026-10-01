import { readFileSync } from 'node:fs';
import { MastraClient } from '@mastra/client-js';

function readFrontendEnv(key: string): string {
  const env = readFileSync('frontend/.env', 'utf8');
  const line = env.split(/\r?\n/).find((l) => l.startsWith(key + '='));
  return line ? line.slice(key.length + 1).trim() : '';
}

const token = readFrontendEnv('VITE_MASTRA_JWT');

// 1) Cliente SIN token → debe fallar (401)
console.log('--- cliente SIN token ---');
try {
  const anon = new MastraClient({ baseUrl: 'http://localhost:4111' });
  await anon
    .getAgent('cafebot-agent')
    .generate([{ role: 'user', content: 'Hola' }], { memory: { thread: 'x' } });
  console.log('anónimo: NO bloqueado (?)');
} catch (e) {
  console.log('anónimo: bloqueado →', String(e).slice(0, 90));
}

// 2) Cliente CON token → debe funcionar
console.log('--- cliente CON token ---');
const client = new MastraClient({
  baseUrl: 'http://localhost:4111',
  headers: { Authorization: `Bearer ${token}` },
});
const res = await client.getAgent('cafebot-agent').generate(
  [{ role: 'user', content: 'Hola, ¿qué cafés de grano tienes?' }],
  { memory: { thread: `auth-${Date.now()}` } },
);
console.log('respuesta:', res.text.slice(0, 200));
process.exit(0);
