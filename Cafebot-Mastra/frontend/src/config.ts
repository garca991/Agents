// URL del backend Mastra (server de `npm run dev`).
export const MASTRA_URL = (import.meta.env.VITE_MASTRA_URL as string | undefined) ?? 'http://localhost:4111';
