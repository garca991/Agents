import { cafebotAgent } from '../src/mastra/agents/cafebot-agent.ts';
import { cafeShopMcpClient } from '../src/mastra/mcp/client.ts';

async function logTools(response: any, etiqueta: string) {
  if (response.toolCalls.length === 0) {
    console.log(`  [${etiqueta}] sin llamadas a tools`);
    return;
  }
  for (const tc of response.toolCalls) {
    console.log(`  -> tool: ${tc.payload.toolName}(${JSON.stringify(tc.payload.args)})`);
  }
  for (const tr of response.toolResults) {
    const re = JSON.stringify(tr.payload.result);
    console.log(`     resultado: ${re.length > 220 ? re.slice(0, 220) + '…' : re}`);
  }
}

console.log('\n========== CASO A: pedido válido en dos turnos ==========');

const turno1 = await cafebotAgent.generate(
  'Hola, quiero pedir 2 unidades del café Geisha de Huila. Me llamo Pepe.',
);
console.log('Usuario:', 'Hola, quiero pedir 2 unidades del café Geisha de Huila. Me llamo Pepe.');
console.log('CaféBot:', turno1.text);
await logTools(turno1, 'turno 1');

const turno2 = await cafebotAgent.generate([
  { role: 'user', content: 'Hola, quiero pedir 2 unidades del café Geisha de Huila. Me llamo Pepe.' },
  { role: 'assistant', content: turno1.text },
  { role: 'user', content: 'Sí, confírmalo por favor.' },
]);
console.log('Usuario:', 'Sí, confírmalo por favor.');
console.log('CaféBot:', turno2.text);
await logTools(turno2, 'turno 2');

console.log('\n========== CASO B: producto inexistente ==========');
const casoB = await cafebotAgent.generate('Quiero 1 unidad del producto con ID PROD-999. Soy Ana.');
console.log('Usuario:', 'Quiero 1 unidad del producto con ID PROD-999. Soy Ana.');
console.log('CaféBot:', casoB.text);
await logTools(casoB, 'caso B');

await cafeShopMcpClient.disconnect();
console.log('\nCliente MCP cerrado.');