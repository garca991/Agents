import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import type { MastraEmbeddingModel } from '@mastra/core/vector';

const openrouter = createOpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY,
});

const base = openrouter.textEmbeddingModel('openai/text-embedding-3-small');

// El provider de OpenRouter emite embeddings "spec v4", pero Mastra (RAG/Memory)
// solo reconoce v3/v2/v1. Este Proxy reporta 'v3' y delega el resto (doEmbed,
// modelId, provider, etc.) al modelo real. La interfaz doEmbed es la misma.
export const cafeEmbedder = new Proxy(base, {
  get(target, prop, receiver) {
    if (prop === 'specificationVersion') return 'v3';
    const value = Reflect.get(target, prop, receiver);
    return typeof value === 'function' ? (value as (...a: unknown[]) => unknown).bind(target) : value;
  },
}) as unknown as MastraEmbeddingModel<string>;
