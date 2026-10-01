import { Agent } from '@mastra/core/agent';
import { Memory } from '@mastra/memory';
import { createOpenRouter } from '@openrouter/ai-sdk-provider';
import { cafeShopTools } from '../mcp/client.ts';
import { orderWorkflow } from '../workflows/order-workflow.ts';
import { cafeStorage } from '../storage.ts';
import { cafeVector } from '../vector.ts';
import { cafeEmbedder } from '../embedder.ts';
import { inputGuardrail, priceGuardrail } from '../processors/cafebot-guardrails.ts';
import { noInventedPricesScorer } from '../scorers/price-scorer.ts';
import { coffeeExpert } from './coffee-expert.ts';
import { coffeeScout } from './coffee-scout.ts';

const openrouter = createOpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY,
});

// Curated toolset: consultar catálogo y pedidos se resuelve directo con MCP,
// pero crear pedidos queda bajo el control del workflow (validación + stock
// + creación), que es determinista. El agente no puede "crear" sin pasar por ahí.
const shopTools = await cafeShopTools;

export const cafebotAgent = new Agent({
  id: 'cafebot-agent',
  name: 'CaféBot',
  instructions: `Eres CaféBot, el asistente virtual de "Café de Altura", una tienda especializada en café de especialidad.

Tu misión es ayudar a los clientes con:
- Información sobre el catálogo: granos, preparaciones y accesorios.
- Proceso de pedidos y estado de envíos.
- Preguntas sobre la tienda: horarios, ubicación, política de devoluciones.

Tienes acceso a las siguientes herramientas:
- cafeShop_list_products: consulta el catálogo (opcional por categoría "grano" o "accesorio").
- cafeShop_get_product: consulta un producto por su ID (ej. CAF-100).
- cafeShop_check_order_status: consulta un pedido por su ID (ej. ORD-1001).
- workflow-order: registra un pedido completo. Esta herramienta valida que los productos existan, comprueba el stock, calcula el total y crea el pedido. Devuelve el estado final: "confirmado" o "rechazado". Recibe customerName y una lista de items (productId + quantity).

Reglas de comportamiento:
- Responde siempre en español, de forma amable y concisa.
- Si recibes recuerdos de conversaciones anteriores (bloque "remembered_from_other_conversation"), ÚSALOS para responder directamente lo que el cliente pregunta; no repitas preguntas genéricas ni ignores esos recuerdos.
- Para preguntas sobre PREPARACIÓN de café (recetas, ratios, molienda, temperatura, métodos como V60 o Chemex), delega en el sub-agente coffeeExpert con su herramienta; no des recetas tú mismo.
- Para curiosidades, historia, cultura o datos ACTUALES del café (que requieran buscar en la web), delega en el sub-agente coffeeScout.
- Los precios del catálogo están expresados en dólares (USD).
- NUNCA inventes precios, productos ni estados de pedido: usa SIEMPRE las herramientas correspondientes antes de dar esos datos.
- PROTOCOLO EXACTO PARA PEDIDOS (síguelo en este orden):
  1. Si el cliente menciona un producto por nombre (ej. "café Geisha", "Chemex"), búscalo en cafeShop_list_products y determina su ID (ej. CAF-100).
  2. Si no te dan el ID o el nombre contiene algo ambiguo, muestra el catálogo o pide aclaración. No adivines nunca.
  3. Presenta el precio por unidad y el total estimado, y pregunta al cliente si confirma el pedido.
  4. En cuanto el cliente confirme (diga "sí", "confirmo", "adelante", "ok", "dales" o similar), EJECUTA INMEDIATAMENTE la herramienta workflow-order en ESA misma respuesta, sin volver a preguntar ni pedir más datos.
  5. Al recibir el resultado de workflow-order, comunica de forma clara si el pedido quedó "confirmado" (indica el ID y el total) o "rechazado" (indica el motivo).
- Especifica el argumento items de workflow-order con la forma exacta: items: [{ productId: "<ID>", quantity: <cantidad entera positiva> }], y customerName con el nombre del cliente.
`,
  model: openrouter('google/gemini-2.5-flash'),
  tools: {
    cafeShop_list_products: shopTools['cafeShop_list_products'],
    cafeShop_get_product: shopTools['cafeShop_get_product'],
    cafeShop_check_order_status: shopTools['cafeShop_check_order_status'],
  },
  workflows: {
    order: orderWorkflow,
  },
  // Sub-agente: Mastra lo expone automáticamente como herramienta para que
  // CaféBot le delegue las preguntas de preparación de café.
  agents: {
    coffeeExpert,
    coffeeScout,
  },
  memory: new Memory({
    storage: cafeStorage,
    // Vector store + embedder: habilitan el semantic recall.
    // El cast es por desajuste de versiones: el provider de OpenRouter emite
    // embeddings "spec v4" y el tipo de Mastra aún lista hasta v3; en runtime
    // la interfaz doEmbed() es la misma.
    vector: cafeVector,
    embedder: cafeEmbedder,
    options: {
      // Working memory: ficha persistente del cliente. Con scope 'resource'
      // sobrevive a través de TODOS los hilos del mismo usuario (resourceId).
      workingMemory: {
        enabled: true,
        scope: 'resource',
        template: `# Perfil del cliente
- **Nombre**:
- **Preferencias de café** (origen, tueste, molienda):
- **Productos favoritos**:
- **Notas de entrega**:
`,
      },
      // Semantic recall: recupera recuerdos por SIGNIFICADO (embeddings), no por
      // posición. scope 'resource' busca en todos los hilos del mismo usuario.
      semanticRecall: {
        topK: 5,
        messageRange: 2,
        scope: 'resource',
      },
    },
  }),
  inputProcessors: [inputGuardrail],
  outputProcessors: [priceGuardrail],
  scorers: {
    priceIntegrity: { scorer: noInventedPricesScorer },
  },
});