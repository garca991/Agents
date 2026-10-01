import { createClient } from '@libsql/client';
import { cafebotAgent } from '../src/mastra/agents/cafebot-agent.ts';

const db = createClient({ url: 'file:D:/Mastra/CursoMastra/data/cafebot.db' });
const rows = async (sql: string) => (await db.execute(sql)).rows as unknown as Record<string, unknown>[];

const resource = `test-sem-${Date.now()}`;
const threadA = `a-${Date.now()}`;
const threadB = `b-${Date.now()}`;

const incidente = 'Hace tres semanas compré un Molinillo manual de acero (ACC-202) y se me rompió la manivela.';
const pregunta = '¿Qué problema tuve con el molinillo que compré?';

console.log(`resource = ${resource}\n`);

console.log('── HILO A (guarda un incidente, SIN decirlo en la ficha) ──');
const a = await cafebotAgent.generate(incidente, { memory: { thread: threadA, resource } });
console.log(a.text.slice(0, 220));

console.log('\n── HILO B (conversación NUEVA, mismo usuario) ──');
const b = await cafebotAgent.generate(pregunta, { memory: { thread: threadB, resource } });
console.log(b.text.slice(0, 400));

// Evidencia: comprobar que NO es la working memory
const wm = (await rows(`SELECT workingMemory FROM mastra_resources WHERE id='${resource}'`))[0]?.workingMemory ?? '';
const vecs = (await rows(`SELECT COUNT(*) AS n FROM memory_messages WHERE metadata LIKE '%${resource}%'`))[0].n as number;

console.log('\n── EVIDENCIA ──');
console.log('working memory (puede tener el producto, pero NO el detalle del incidente):');
console.log('  ', String(wm).replace(/\n/g, ' | ').slice(0, 180));
const enFicha = /manivela/i.test(String(wm));
console.log('¿la ficha contiene "manivela"?', enFicha, enFicha ? '(está en la ficha → prueba NO concluyente)' : '(no está en la ficha ⇒ el detalle vino del recall)');
console.log('vectores indexados de este resource:', vecs);

const recordado = /manivela|ACC-202|se rompió|se rompio/i.test(b.text);
console.log(
  recordado
    ? '\n✅ PASS — el hilo B recordó el incidente de otro hilo (semantic recall OK)'
    : '\n❌ FAIL — no lo recordó',
);

await db.close();
process.exit(0);