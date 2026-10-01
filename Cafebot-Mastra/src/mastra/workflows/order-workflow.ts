import { createStep, createWorkflow } from '@mastra/core/workflows';
import { noopObserve } from '@mastra/core/tools';
import type { RequestContext } from '@mastra/core/request-context';
import { z } from 'zod';
import { cafeShopTools } from '../mcp/client.ts';

const itemSchema = z.object({
  productId: z.string(),
  quantity: z.number().int().positive(),
});

const validatedItemSchema = z.object({
  productId: z.string(),
  name: z.string(),
  quantity: z.number(),
  unitPrice: z.number(),
});

const validateOutputSchema = z.object({
  valid: z.boolean(),
  customerName: z.string(),
  items: z.array(validatedItemSchema),
  total: z.number(),
  error: z.string().nullable(),
});

const branchOutputSchema = z.object({
  status: z.string(),
  orderId: z.string().nullable(),
  total: z.number().nullable(),
  error: z.string().nullable(),
});

// Al llamar una tool desde código (y no desde un agente) hay que darle
// el contexto de ejecución que normalmente aporta el runtime de Mastra.
async function shopTool(name: string, input: Record<string, unknown>, requestContext: RequestContext) {
  const tool = (await cafeShopTools)[name];
  if (!tool?.execute) throw new Error(`Tool MCP no disponible: ${name}`);
  return tool.execute(input, { requestContext, observe: noopObserve });
}

const validateOrder = createStep({
  id: 'validate-order',
  inputSchema: z.object({
    customerName: z.string(),
    items: z.array(itemSchema),
  }),
  outputSchema: validateOutputSchema,
  execute: async ({ inputData, requestContext }) => {
    const validatedItems: z.infer<typeof validatedItemSchema>[] = [];
    let total = 0;

    for (const item of inputData.items) {
      const result = await shopTool('cafeShop_get_product', { productId: item.productId }, requestContext);
      const product = result.product;
      if (!product) {
        return {
          valid: false,
          customerName: inputData.customerName,
          items: [],
          total: 0,
          error: `Producto inexistente: ${item.productId}`,
        };
      }
      validatedItems.push({
        productId: product.id,
        name: product.name,
        quantity: item.quantity,
        unitPrice: product.price,
      });
      total += product.price * item.quantity;
    }

    return {
      valid: true,
      customerName: inputData.customerName,
      items: validatedItems,
      total,
      error: null,
    };
  },
});

const rejectOrder = createStep({
  id: 'reject-order',
  inputSchema: validateOutputSchema,
  outputSchema: branchOutputSchema,
  execute: async ({ inputData }) => ({
    status: 'rechazado',
    orderId: null,
    total: null,
    error: inputData.error,
  }),
});

const processOrder = createStep({
  id: 'process-order',
  inputSchema: validateOutputSchema,
  outputSchema: branchOutputSchema,
  execute: async ({ inputData, requestContext }) => {
    const result = await shopTool(
      'cafeShop_create_order',
      {
        customerName: inputData.customerName,
        items: inputData.items.map((item) => ({
          productId: item.productId,
          quantity: item.quantity,
        })),
      },
      requestContext,
    );

    if (result.error) {
      return { status: 'rechazado', orderId: null, total: null, error: result.error };
    }

    return {
      status: 'confirmado',
      orderId: result.order?.id ?? null,
      total: result.order?.total ?? null,
      error: null,
    };
  },
});

const formatResult = createStep({
  id: 'format-result',
  inputSchema: z.object({
    'reject-order': branchOutputSchema.optional(),
    'process-order': branchOutputSchema.optional(),
  }),
  outputSchema: branchOutputSchema,
  execute: async ({ inputData }) => {
    const result = inputData['reject-order'] ?? inputData['process-order'];
    if (!result) throw new Error('Ninguna rama del workflow se ejecutó');
    return result;
  },
});

export const orderWorkflow = createWorkflow({
  id: 'order-workflow',
  description:
    'Registra un pedido de Café de Altura de principio a fin: valida que los productos existan, comprueba el stock, calcula el total y crea el pedido en el sistema. Devuelve el estado final: confirmado o rechazado.',
  inputSchema: z.object({
    customerName: z.string(),
    items: z.array(itemSchema),
  }),
  outputSchema: branchOutputSchema,
})
  .then(validateOrder)
  .branch([
    [async (input) => input.inputData.valid === false, rejectOrder],
    [async (input) => input.inputData.valid === true, processOrder],
  ])
  .then(formatResult)
  .commit();