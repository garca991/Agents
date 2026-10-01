import { orderWorkflow } from '../src/mastra/workflows/order-workflow.ts';
import { cafeShopMcpClient } from '../src/mastra/mcp/client.ts';

async function runCase(nombre: string, input: { customerName: string; items: { productId: string; quantity: number }[] }) {
  console.log(`\n========== CASO: ${nombre} ==========`);
  console.log('Entrada:', JSON.stringify(input));

  const run = await orderWorkflow.createRun();
  const result = await run.start({ inputData: input });

  console.log(`Estado del run: ${result.status}`);

  console.log('Pasos ejecutados:');
  for (const [stepId, stepResult] of Object.entries(result.steps)) {
    console.log(`  - ${stepId}: estado=${stepResult.status}`);
    if (stepResult.status === 'success') {
      console.log(`      output=${JSON.stringify(stepResult.output)}`);
    }
  }

  if (result.status === 'success') {
    console.log('Salida final:', JSON.stringify(result.result));
  } else {
    console.log('Error:', JSON.stringify((result as any).error));
  }

  return result;
}

await runCase('pedido válido', {
  customerName: 'Pepe',
  items: [{ productId: 'CAF-100', quantity: 2 }],
});

await runCase('producto inexistente', {
  customerName: 'Pepe',
  items: [{ productId: 'PROD-999', quantity: 1 }],
});

await runCase('pedido mixto', {
  customerName: 'Ana',
  items: [
    { productId: 'CAF-102', quantity: 1 },
    { productId: 'ACC-201', quantity: 1 },
  ],
});

await runCase('stock insuficiente', {
  customerName: 'Luis',
  items: [{ productId: 'ACC-202', quantity: 99 }],
});

await cafeShopMcpClient.disconnect();