import { createScorer } from '@mastra/core/evals';
import { catalogUnitPrices, reachableTotals, mentionedPrices } from '../pricing.ts';

// Extrae el texto plano de un mensaje de Mastra ({ format: 2, parts: [...] }).
function messageText(message: { content?: unknown }): string {
  const content = message.content;
  if (typeof content === 'string') return content;
  if (content && typeof content === 'object') {
    const parts = (content as { parts?: unknown }).parts;
    if (Array.isArray(parts)) {
      return parts
        .filter((p) => p && typeof p === 'object' && (p as { type?: unknown }).type === 'text')
        .map((p) => String((p as { text?: unknown }).text ?? ''))
        .join(' ');
    }
  }
  return '';
}

function outputText(run: { output?: unknown }): string {
  const output = run.output;
  if (!Array.isArray(output)) return '';
  return output.map((m) => messageText(m as { content?: unknown })).join('\n');
}

// Scorer de integridad de precios: 1 si TODOS los precios mencionados son del
// catálogo (unitarios o totales alcanzables); 0 si hay alguno inventado.
export const noInventedPricesScorer = createScorer({
  id: 'no-invented-prices',
  description: 'Comprueba que todos los precios mencionados existan en el catálogo',
})
  .generateScore(async ({ run }) => {
    const unitPrices = await catalogUnitPrices();
    if (!unitPrices.length) return 1; // fail-open si el catálogo no responde
    const allowed = new Set<number>([...unitPrices, ...reachableTotals(unitPrices)]);
    const mentioned = mentionedPrices(outputText(run));
    if (mentioned.length === 0) return 1;
    return mentioned.every((value) => allowed.has(value)) ? 1 : 0;
  })
  .generateReason(async ({ run, score }) => {
    const mentioned = mentionedPrices(outputText(run));
    if (mentioned.length === 0) return 'No se mencionaron precios.';
    return score === 1
      ? `OK: todos los precios (${mentioned.join(', ')}) existen en el catálogo.`
      : `Precio fuera de catálogo detectado: ${mentioned.join(', ')}`;
  });
