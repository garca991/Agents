import { createClient } from '@libsql/client';
import { mastra } from '../src/mastra/index.ts';
import { noInventedPricesScorer } from '../src/mastra/scorers/price-scorer.ts';

const DATASET_ID = 'price-integrity';

// 1) (Re)crear el dataset limpio
try {
  await mastra.datasets.delete({ id: DATASET_ID });
} catch {
  // no existía
}
const dataset = await mastra.datasets.create({
  id: DATASET_ID,
  name: 'Integridad de precios',
  description: 'Preguntas de catálogo para medir que CaféBot no invente precios.',
});

// 2) Casos de prueba (input + respuesta esperada)
await dataset.addItems({
  items: [
    { input: '¿Cuánto cuesta el Geisha de Huila?', groundTruth: { price: 18 } },
    { input: '¿Cuánto cuesta la Cafetera Chemex 6 tazas?', groundTruth: { price: 45 } },
    { input: '¿Cuánto cuesta el Molinillo manual de acero?', groundTruth: { price: 35 } },
    { input: '¿Cuánto cuesta el Filtro de papel V60 (100 uds)?', groundTruth: { price: 12 } },
  ],
});
console.log('Dataset listo:', DATASET_ID, '(4 casos)\n');

// 3) Correr el experimento: ejecuta el agente en cada caso y aplica el scorer
const summary = await dataset.startExperiment({
  targetType: 'agent',
  targetId: 'cafebot-agent',
  scorers: [noInventedPricesScorer],
  name: 'precios-v1',
  maxConcurrency: 2,
});

console.log('=== RESULTADO DEL EXPERIMENTO ===');
console.log(`status: ${summary.status} | ${summary.succeededCount}/${summary.totalItems} ok | fallidos: ${summary.failedCount}`);
for (const r of summary.results) {
  const s = r.scores[0];
  console.log(`  · "${String(r.input).slice(0, 48)}"`);
  console.log(`      score=${s?.score} | ${s?.reason}`);
}

// 4) Verificar persistencia
const db = createClient({ url: 'file:D:/Mastra/CursoMastra/data/cafebot.db' });
const count = async (t: string) =>
  ((await db.execute(`SELECT COUNT(*) AS n FROM ${t}`)).rows[0] as unknown as { n: number }).n;
console.log('\n=== PERSISTIDO EN LA DB ===');
console.log('  mastra_datasets:', await count('mastra_datasets'));
console.log('  mastra_dataset_items:', await count('mastra_dataset_items'));
console.log('  mastra_experiments:', await count('mastra_experiments'));
console.log('  mastra_experiment_results:', await count('mastra_experiment_results'));
await db.close();
process.exit(0);