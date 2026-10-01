import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { MDocument } from '@mastra/rag';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import { cafeVector } from '../src/mastra/vector.ts';

const INDEX = 'coffee_recipes';
const FUENTE = 'recetas-cafe.md';

const openrouter = createOpenRouter({ apiKey: process.env.OPENROUTER_API_KEY });
const embedder = openrouter.textEmbeddingModel('openai/text-embedding-3-small');

// 1) Dividir el documento en secciones por título "## " (una receta por sección).
const raw = readFileSync(resolve('src/mastra/knowledge/recetas-cafe.md'), 'utf8');
const secciones = raw
  .split(/\n(?=## )/)
  .map((s) => s.trim())
  .filter(Boolean);

// 2) Chunkear cada sección (usualmente 1 chunk por receta, cabecera incluida).
const chunks: { text: string; title: string }[] = [];
for (const seccion of secciones) {
  const title = (seccion.match(/^#+\s*(.+)/m)?.[1] ?? 'Introducción').trim();
  const doc = MDocument.fromMarkdown(seccion);
  const partes = await doc.chunk({ strategy: 'markdown', maxSize: 1500, overlap: 0 });
  for (const c of partes) chunks.push({ text: c.text, title });
}
console.log('secciones:', secciones.length, '| chunks:', chunks.length);
chunks.forEach((c, i) => console.log(`  [${i}] ${c.title} → ${c.text.replace(/\n/g, ' ').slice(0, 70)}`));

// 3) Embeddings
const res = (await embedder.doEmbed({ values: chunks.map((c) => c.text) })) as unknown as {
  embeddings: number[][];
};
const vectors = res.embeddings;

// 4) (Re)crear índice y guardar
try {
  await cafeVector.deleteIndex({ indexName: INDEX });
} catch {
  // no existía
}
await cafeVector.createIndex({ indexName: INDEX, dimension: vectors[0].length, metric: 'cosine' });

const ids = await cafeVector.upsert({
  indexName: INDEX,
  vectors,
  metadata: chunks.map((c) => ({ text: c.text, title: c.title, source: FUENTE })),
});
console.log('\nupsert OK →', ids.length, 'vectores en', INDEX);
process.exit(0);