import { MCPClient } from '@mastra/mcp';
import { dirname, join, resolve } from 'node:path';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

function findProjectRoot(startDir: string): string {
  let dir = startDir;
  for (;;) {
    if (existsSync(join(dir, 'mcp-server', 'src', 'index.ts'))) return dir;
    const parent = dirname(dir);
    if (parent === dir) throw new Error('No se encontró el directorio que contiene mcp-server/');
    dir = parent;
  }
}

const projectRoot = findProjectRoot(dirname(fileURLToPath(import.meta.url)));

export const cafeShopMcpClient = new MCPClient({
  id: 'cafe-shop-mcp',
  servers: {
    cafeShop: {
      command: 'node',
      args: [resolve(projectRoot, 'mcp-server/src/index.ts')],
      cwd: projectRoot,
    },
  },
});

export const cafeShopTools = cafeShopMcpClient.listTools();