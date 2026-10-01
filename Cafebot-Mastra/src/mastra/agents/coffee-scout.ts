import { Agent } from '@mastra/core/agent';
import { Memory } from '@mastra/memory';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import { cafeStorage } from '../storage.ts';
import { wikipediaSearch } from '../tools/wikipedia.ts';

const openrouter = createOpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY,
});

// Sub-agente "explorador": responde curiosidades, historia y cultura del café
// usando la tool de Wikipedia (gratis, sin key). Modelo con soporte de tools.
export const coffeeScout = new Agent({
  id: 'coffee-scout',
  name: 'Explorador de Café',
  description:
    'Explorador que responde curiosidades, historia y cultura del café consultando Wikipedia y citando la fuente.',
  instructions: `Eres el "Explorador de Café" de "Café de Altura": un investigador que responde con información enciclopédica.

Tu especialidad:
- Curiosidades, historia, cultura y orígenes del café.

Reglas:
- Responde siempre en español, claro y conciso.
- Para CUALQUIER dato histórico o de cultura, usa SIEMPRE la herramienta wikipedia-search antes de responder.
- Básate en lo que devuelva la herramienta y CITA la fuente (título + URL).
- Si no encuentras información fiable, dilo con honestidad.
- No des recetas ni métodos de preparación (eso es del barista). No gestiones pedidos ni catálogo.
`,
  model: openrouter('google/gemini-2.5-flash'),
  tools: { wikipediaSearch },
  // Memory propia y mínima: evita heredar la working memory del padre.
  memory: new Memory({ storage: cafeStorage }),
});
