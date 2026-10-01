import { createScorer } from '@mastra/core/evals';
import { mastra } from '../src/mastra/index.ts';
import { noInventedPricesScorer } from '../src/mastra/scorers/price-scorer.ts';
import { mentionedPrices } from '../src/mastra/pricing.ts';

// Extrae el texto plano de la salida del agente (MastraDBMessage[]).
function textOf(run: { output?: unknown }): string {
  const output = run.output;
  if (!Array.isArray(output)) return '';
  return output
    .map((m) => {
      const content = (m as { content?: { parts?: { type?: string; text?: string }[] } }).content;
      return (content?.parts ?? []).filter((p) => p.type === 'text').map((p) => p.text ?? '').join(' ');
    })
    .join('\n');
}

// Scorer ESTRICTO (v2): exige que la respuesta mencione el precio esperado.
const priceMatchesExpectedScorer = createScorer({
  id: 'price-matches-expected',
  description: 'Comprueba que la respuesta mencione el precio esperado (groundTruth)',
})
  .generateScore(({ run }) => {
    const expected = (run as { groundTruth?: { price?: number } }).groundTruth?.price;
    if (typeof expected !== 'number') return 1;
    return mentionedPrices(textOf(run)).includes(expected) ? 1 : 0;
  })
  .generateReason(({ run, score }) => {
    const expected = (run as { groundTruth?: { price?: number } }).groundTruth?.price;
    return score === 1
      ? `Mencionó el precio esperado ($${expected}).`
      : `No mencionó el precio esperado ($${expected}).`;
  });

const CASOS = [
  { input: '¿Cuánto cuesta el Geisha de Huila?', groundTruth: { price: 18 } },
  { input: '¿Cuánto cuesta la Cafetera Chemex 6 tazas?', groundTruth: { price: 45 } },
  { input: '¿Cuánto cuesta el Molinillo manual de acero?', groundTruth: { price: 35 } },
  { input: '¿Cuánto cuesta el Filtro de papel V60 (100 uds)?', groundTruth: { price: 12 } },
];

// Dataset limpio
try {
  await mastra.datasets.delete({ id: 'price-integrity' });
} catch {}
const dataset = await mastra.datasets.create({
  id: 'price-integrity',
  name: 'Integridad de precios',
  description: 'Comparación de dos versiones de scorer.',
});
await dataset.addItems({ items: CASOS });
console.log('Dataset listo (4 casos)\n');

// Experimento v1 (scorer de catálogo) y v2 (scorer estricto)
const v1 = await dataset.startExperiment({
  targetType: 'agent',
  targetId: 'cafebot-agent',
  scorers: [noInventedPricesScorer],
  name: 'v1-catalogo',
  maxConcurrency: 2,
});
console.log(`v1 (catalogo): ${v1.succeededCount}/${v1.totalItems} ok`);

const v2 = await dataset.startExperiment({
  targetType: 'agent',
  targetId: 'cafebot-agent',
  scorers: [priceMatchesExpectedScorer],
  name: 'v2-estricto',
  maxConcurrency: 2,
});
console.log(`v2 (estricto): ${v2.succeededCount}/${v2.totalItems} ok\n`);

// Comparar
const cmp = await mastra.datasets.compareExperiments({
  experimentIds: [v1.experimentId, v2.experimentId],
  baselineId: v1.experimentId,
});

console.log('=== COMPARACIÓN (baseline = v1) ===');
for (const it of cmp.items) {
  console.log(`· ${String(it.input).slice(0, 52)}`);
  for (const [expId, r] of Object.entries(it.results)) {
    const label = expId === v1.experimentId ? 'v1' : 'v2';
    console.log(`    ${label}: ${JSON.stringify(r?.scores)}`);
  }
}
process.exit(0);