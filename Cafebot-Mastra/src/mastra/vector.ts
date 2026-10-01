import { LibSQLVector } from '@mastra/libsql';
import { cafeDbUrl } from './storage.ts';

// Vector store para el semantic recall. LibSQL soporta vectores nativamente,
// así que reutilizamos la MISMA base de datos (data/cafebot.db) — sin servicio externo.
export const cafeVector = new LibSQLVector({
  id: 'cafe-vectors',
  url: cafeDbUrl,
});
