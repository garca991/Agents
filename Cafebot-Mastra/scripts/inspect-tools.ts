import { cafeShopTools, cafeShopMcpClient } from '../src/mastra/mcp/client.ts';

console.log('Conectando al servidor MCP cafe-shop-mcp (stdio)...');
console.log('');

const tools = await cafeShopTools;
const names = Object.keys(tools);

console.log(`Descubiertas ${names.length} herramientas:\n`);
for (const name of names) {
  const tool = tools[name];
  console.log(`- ${name}`);
  console.log(`  descripción : ${tool.description}`);
  console.log(`  tiene execute: ${Boolean(tool.execute)}`);
  console.log('');
}

console.log('--- Detalle del inputSchema de la primera tool ---');
const first = tools[names[0]];
const short = (schema: any) => {
  if (!schema) return '(sin schema)';
  try {
    return JSON.stringify(schema, null, 2);
  } catch {
    return String(schema);
  }
};
console.log(short(first.inputSchema));

await cafeShopMcpClient.disconnect();
console.log('Cliente MCP cerrado.');