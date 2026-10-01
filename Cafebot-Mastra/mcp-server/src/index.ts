import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import * as z from 'zod/v4';

const products = [
  { id: 'CAF-100', name: 'Geisha de Huila', category: 'grano', origin: 'Colombia', tasting: 'Jazmín, cítricos y miel', price: 18, stock: 25 },
  { id: 'CAF-101', name: 'Yirgacheffe', category: 'grano', origin: 'Etiopía', tasting: 'Bergamota, limón y durazno', price: 16, stock: 18 },
  { id: 'CAF-102', name: 'Santuario Brasileño', category: 'grano', origin: 'Brasil', tasting: 'Chocolate, avellana y caramelo', price: 14, stock: 30 },
  { id: 'ACC-200', name: 'Filtro de papel V60 (100 uds)', category: 'accesorio', price: 12, stock: 50 },
  { id: 'ACC-201', name: 'Cafetera Chemex 6 tazas', category: 'accesorio', price: 45, stock: 12 },
  { id: 'ACC-202', name: 'Molinillo manual de acero', category: 'accesorio', price: 35, stock: 8 },
];

let orders = [
  {
    id: 'ORD-1001',
    customerName: 'Ana',
    status: 'enviado',
    items: [{ productId: 'CAF-100', quantity: 1 }],
    total: 18,
    estimatedDelivery: '2026-09-19',
  },
  {
    id: 'ORD-1002',
    customerName: 'Luis',
    status: 'en_proceso',
    items: [{ productId: 'ACC-201', quantity: 1 }],
    total: 45,
    estimatedDelivery: null,
  },
  {
    id: 'ORD-1003',
    customerName: 'Marta',
    status: 'entregado',
    items: [{ productId: 'CAF-101', quantity: 2 }],
    total: 32,
    estimatedDelivery: null,
  },
];

let orderCounter = 1004;

const productSchema = z.object({
  id: z.string(),
  name: z.string(),
  category: z.string(),
  origin: z.string().nullable().optional(),
  tasting: z.string().nullable().optional(),
  price: z.number(),
  stock: z.number(),
});

const orderSchema = z.object({
  id: z.string(),
  customerName: z.string(),
  status: z.string(),
  items: z.array(z.object({ productId: z.string(), quantity: z.number() })),
  total: z.number(),
  estimatedDelivery: z.string().nullable(),
});

const server = new McpServer({ name: 'cafe-shop-mcp', version: '1.0.0' });

server.registerTool(
  'list_products',
  {
    description:
      'Lista los productos del catálogo de Café de Altura. Filtra por categoría si se indica ("grano" o "accesorio").',
    inputSchema: {
      category: z.string().optional().describe("Categoría: 'grano' o 'accesorio'"),
    },
    outputSchema: {
      products: z.array(productSchema),
    },
  },
  async ({ category }) => {
    const filtered = category ? products.filter((p) => p.category === category) : products;
    return {
      content: [{ type: 'text', text: JSON.stringify(filtered) }],
      structuredContent: { products: filtered },
    };
  },
);

server.registerTool(
  'get_product',
  {
    description: 'Devuelve los detalles de un producto del catálogo por su ID (ej. CAF-100, ACC-201).',
    inputSchema: {
      productId: z.string().describe('ID del producto'),
    },
    outputSchema: {
      product: productSchema.nullable(),
    },
  },
  async ({ productId }) => {
    const product = products.find((p) => p.id === productId.trim().toUpperCase()) ?? null;
    return {
      content: [{ type: 'text', text: product ? JSON.stringify(product) : `Producto no encontrado: ${productId}` }],
      structuredContent: { product },
    };
  },
);

server.registerTool(
  'check_order_status',
  {
    description:
      'Devuelve el estado de un pedido de la tienda por su ID (ej. ORD-1001). Estados: recibido, en_proceso, enviado, entregado.',
    inputSchema: {
      orderId: z.string().describe('ID del pedido'),
    },
    outputSchema: {
      order: orderSchema.nullable(),
    },
  },
  async ({ orderId }) => {
    const order = orders.find((o) => o.id === orderId.trim().toUpperCase()) ?? null;
    return {
      content: [
        { type: 'text', text: order ? JSON.stringify(order) : `Pedido no encontrado: ${orderId}` },
      ],
      structuredContent: { order },
    };
  },
);

server.registerTool(
  'create_order',
  {
    description:
      'Crea un pedido nuevo en la tienda. Recibe el nombre del cliente y una lista de items (productId + cantidad). Valida stock y calcula el total.',    inputSchema: {
      customerName: z.string().describe('Nombre del cliente'),
      items: z
        .array(
          z.object({
            productId: z.string().describe('ID del producto'),
            quantity: z.number().int().positive().describe('Cantidad a comprar'),
          }),
        )
        .describe('Lista de productos solicitados'),
    },
    outputSchema: {
      order: orderSchema.nullable(),
      error: z.string().nullable(),
    },
  },
  async ({ customerName, items }) => {
    const orderItems: { productId: string; quantity: number }[] = [];
    let total = 0;

    for (const item of items) {
      const product = products.find((p) => p.id === item.productId.trim().toUpperCase());
      if (!product) {
        return {
          content: [{ type: 'text', text: `Producto inexistente: ${item.productId}` }],
          structuredContent: { order: null, error: `Producto inexistente: ${item.productId}` },
        };
      }
      if (product.stock < item.quantity) {
        return {
          content: [
            { type: 'text', text: `Stock insuficiente para ${product.name} (${product.stock} disponibles)` },
          ],
          structuredContent: {
            order: null,
            error: `Stock insuficiente para ${product.name}`,
          },
        };
      }
      orderItems.push({ productId: product.id, quantity: item.quantity });
      total += product.price * item.quantity;
    }

    const order = {
      id: `ORD-${orderCounter++}`,
      customerName,
      status: 'recibido',
      items: orderItems,
      total,
      estimatedDelivery: null,
    };
    orders.push(order);
    return {
      content: [{ type: 'text', text: JSON.stringify(order) }],
      structuredContent: { order, error: null },
    };
  },
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('MCP server cafe-shop-mcp corriendo sobre stdio');
}

main().catch((error) => {
  console.error('Error en el MCP server:', error);
  process.exit(1);
});