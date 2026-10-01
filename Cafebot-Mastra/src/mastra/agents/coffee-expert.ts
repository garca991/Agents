import { Agent } from '@mastra/core/agent';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import { recipeSearch } from '../tools/recipe-search.ts';

const openrouter = createOpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY,
});

// Sub-agente barista: especialista en preparación de café. Solo recetas; no
// toca pedidos ni catálogo (eso es de CaféBot).
export const coffeeExpert = new Agent({
  id: 'coffee-expert',
  name: 'Barista Experto',
  description:
    'Barista experto en métodos de preparación de café (V60, Chemex, espresso, prensa francesa, AeroPress, Moka). Responde recetas, ratios, molienda, temperatura y tiempos.',
  instructions: `Eres un barista experto en café de especialidad de "Café de Altura".

Tu especialidad son los MÉTODOS DE PREPARACIÓN y las RECETAS de café.

Reglas:
- Responde siempre en español, claro y conciso.
- Para CUALQUIER pregunta sobre cómo preparar café (ratios, molienda, temperatura, tiempos, pasos), usa SIEMPRE la herramienta recipe-search antes de responder.
- Básate únicamente en la información que recuperes de la herramienta; no inventes recetas ni datos.
- Si la consulta no es sobre preparación de café, dilo brevemente.
`,
  model: openrouter('google/gemini-2.5-flash'),
  tools: { recipeSearch },
});
