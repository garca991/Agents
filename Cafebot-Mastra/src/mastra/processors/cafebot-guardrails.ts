import type {
  InputProcessor,
  OutputProcessor,
  ProcessInputArgs,
  ProcessOutputResultArgs,
} from '@mastra/core/processors';
import { catalogUnitPrices, reachableTotals, mentionedPrices } from '../pricing.ts';

// Mastra guarda el mensaje como { format: 2, parts: [...] }. Esto extrae el texto plano.
function messageText(message: { content?: unknown }): string {
  const content = message.content;
  if (!content || typeof content !== 'object') return '';
  const parts = (content as { parts?: unknown }).parts;
  if (!Array.isArray(parts)) return '';
  const out: string[] = [];
  for (const part of parts) {
    if (part && typeof part === 'object' && (part as { type?: unknown }).type === 'text') {
      const text = (part as { text?: unknown }).text;
      if (typeof text === 'string') out.push(text);
    }
  }
  return out.join(' ').trim();
}

// ---------------------------------------------------------------------------
// 1) Guardrail de ENTRADA: corta intentos de manipular al agente (prompt
//    injection / jailbreak) antes de que lleguen al modelo.
// ---------------------------------------------------------------------------
const INJECTION_PATTERNS: RegExp[] = [
  /ignora (todas )?(tus|las) (instrucciones|reglas|indicaciones)/i,
  /olvida (tus|las) (instrucciones|reglas|indicaciones)/i,
  /(revela|muestra|dime) (tu|el) (prompt|system|instrucciones)/i,
  /(system|developer) (prompt|message)/i,
  /act[uú]a como (si fueras|un|una)/i,
  /jailbreak|dan mode|modo desarrollador/i,
];

export const inputGuardrail: InputProcessor = {
  id: 'cafebot-input-guard',
  name: 'Guardrail de entrada de CaféBot',
  processInput({ messages, abort }: ProcessInputArgs) {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    const text = lastUser ? messageText(lastUser) : '';
    const hit = INJECTION_PATTERNS.find((re) => re.test(text));
    if (hit) {
      abort('No puedo ayudarte con esa petición. ¿Te ayudo con nuestro catálogo de café?', {
        metadata: { regla: hit.source },
      });
    }
    return messages;
  },
};

// ---------------------------------------------------------------------------
// 2) Guardrail de SALIDA: impide que CaféBot invente precios. Un precio es
//    válido si es un precio unitario del catálogo o una suma alcanzable con
//    los productos del catálogo (totales/subtotales).
// ---------------------------------------------------------------------------
export const priceGuardrail: OutputProcessor = {
  id: 'cafebot-price-guard',
  name: 'Guardrail de precios de CaféBot',
  async processOutputResult({ result, messages, abort }: ProcessOutputResultArgs) {
    let unitPrices: number[];
    try {
      unitPrices = await catalogUnitPrices();
    } catch {
      return messages; // fail-open: si el catálogo no responde, no bloqueamos
    }
    if (!unitPrices.length) return messages;

    const reachable = reachableTotals(unitPrices);
    const allowed = new Set<number>([...unitPrices, ...reachable]);
    const mentioned = mentionedPrices(result.text);
    const invented = mentioned.find((value) => !allowed.has(value));

    if (invented !== undefined) {
      abort(
        `He detectado un precio que no coincide con nuestro catálogo ($${invented}). ` +
          'Déjame confirmarlo con el catálogo antes de dártelo.',
        { metadata: { precio: invented, catalogo: unitPrices } },
      );
    }
    return messages;
  },
};
