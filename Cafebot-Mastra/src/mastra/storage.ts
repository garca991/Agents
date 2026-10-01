import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

import { LibSQLStore } from '@mastra/libsql';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';

// Anclamos la ruta a la raíz del proyecto (el archivo storage.ts vive en
// src/mastra/, así que subimos dos niveles hasta la raíz y colgamos data/ ahí).
// Así la DB no depende del CWD del proceso dev, y vive FUERA de .mastra/ para
// que `mastra build` (que limpia .mastra) no la borre.
const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const dataDir = resolve(projectRoot, 'data');

// libsql NO crea la carpeta destino automáticamente: hay que asegurarla antes.
mkdirSync(dataDir, { recursive: true });

// URL compartida: la usa el storage relacional y el vector store (misma DB).
export const cafeDbUrl = `file:${dataDir.replace(/\\/g, '/')}/cafebot.db`;

export const cafeStorage = new LibSQLStore({
  id: 'cafe-storage',
  url: cafeDbUrl,
});
