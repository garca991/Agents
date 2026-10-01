import { noInventedPricesScorer } from '../src/mastra/scorers/price-scorer.ts';

const msg = (text: string) => ({ role: 'assistant', content: { format: 2, parts: [{ type: 'text', text }] } });

const legitimo = await noInventedPricesScorer.run({
  input: {},
  output: [msg('El Geisha de Huila cuesta $18 y el total por 2 serían $36.')],
});
console.log('PRECIO LEGÍTIMO → score:', legitimo.score, '|', legitimo.reason);

const inventado = await noInventedPricesScorer.run({
  input: {},
  output: [msg('El Geisha de Huila cuesta $25 por unidad.')],
});
console.log('PRECIO INVENTADO → score:', inventado.score, '|', inventado.reason);

process.exit(0);