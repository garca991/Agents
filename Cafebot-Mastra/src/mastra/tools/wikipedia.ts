import { createTool } from '@mastra/core/tools';
import { z } from 'zod';

const LANG = 'es';
const UA = 'CafeBot/1.0 (curso Mastra; contacto: local)';

type WikiResult = { found: boolean; title: string; extract: string; url: string };

async function wikiLookup(query: string): Promise<WikiResult> {
  // 1) Buscar el artículo más relevante
  const searchUrl =
    `https://${LANG}.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=1&srsearch=` +
    encodeURIComponent(query);
  const sres = await fetch(searchUrl, { headers: { 'User-Agent': UA } });
  const sjson = (await sres.json()) as { query?: { search?: { title: string }[] } };
  const title = sjson.query?.search?.[0]?.title;
  if (!title) return { found: false, title: '', extract: '', url: '' };

  // 2) Resumen del artículo
  const sumUrl = `https://${LANG}.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`;
  const ures = await fetch(sumUrl, { headers: { 'User-Agent': UA } });
  if (!ures.ok) return { found: false, title, extract: '', url: '' };
  const ujson = (await ures.json()) as {
    title: string;
    extract?: string;
    content_urls?: { desktop?: { page?: string } };
  };

  return {
    found: true,
    title: ujson.title,
    extract: ujson.extract ?? '',
    url: ujson.content_urls?.desktop?.page ?? `https://${LANG}.wikipedia.org/wiki/${encodeURIComponent(title)}`,
  };
}

// Tool de Wikipedia (español): gratis, sin API key. Devuelve un resumen + fuente.
export const wikipediaSearch = createTool({
  id: 'wikipedia-search',
  description:
    'Busca información en Wikipedia en español. Úsala para historia, cultura, orígenes y datos generales sobre el café. Devuelve un resumen y la URL de la fuente.',
  inputSchema: z.object({
    query: z.string().describe('Tema a buscar, p. ej. "café arábica" o "historia del café"'),
  }),
  execute: async ({ query }) => wikiLookup(query),
});
