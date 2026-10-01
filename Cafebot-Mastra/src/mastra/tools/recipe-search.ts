import { createVectorQueryTool } from '@mastra/rag';
import { cafeVector } from '../vector.ts';
import { cafeEmbedder } from '../embedder.ts';

// Tool de búsqueda RAG sobre la base de conocimiento de recetas (índice
// coffee_recipes). cafeEmbedder adapta el modelo v4 de OpenRouter a v3.
export const recipeSearch = createVectorQueryTool({
  id: 'recipe-search',
  description:
    'Busca recetas y métodos de preparación de café (V60, Chemex, espresso, prensa francesa, AeroPress, Moka) en la base de conocimiento. Úsala antes de responder sobre cómo preparar café.',
  indexName: 'coffee_recipes',
  vectorStore: cafeVector,
  model: cafeEmbedder,
});
