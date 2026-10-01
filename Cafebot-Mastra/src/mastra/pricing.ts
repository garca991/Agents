import { cafeShopTools } from './mcp/client.ts';

// Utilidades de precios compartidas por el guardrail de precios y el scorer de
// integridad de precios. Leen el catálogo real vía la tool MCP.

type ExecutableTool = { execute?: (input: unknown, options: unknown) => Promise<unknown> };

let catalogPricesPromise: Promise<number[]> | undefined;

export async function catalogUnitPrices(): Promise<number[]> {
  catalogPricesPromise ??= (async () => {
    const tools = (await cafeShopTools) as Record<string, ExecutableTool>;
    const list = tools['cafeShop_list_products'];
    const result = (await list?.execute?.({}, {})) as { products?: { price?: unknown }[] } | undefined;
    return (result?.products ?? [])
      .map((p) => p.price)
      .filter((n): n is number => typeof n === 'number' && n > 0);
  })();
  return catalogPricesPromise;
}

// Todas las sumas alcanzables con los precios del catálogo (totales/subtotales).
export function reachableTotals(unitPrices: number[], cap = 1000): Set<number> {
  const reachable = new Set<number>();
  const queue = [0];
  while (queue.length) {
    const current = queue.shift() as number;
    for (const price of unitPrices) {
      const next = current + price;
      if (next <= cap && !reachable.has(next)) {
        reachable.add(next);
        queue.push(next);
      }
    }
  }
  return reachable;
}

export function mentionedPrices(text: string): number[] {
  return [...text.matchAll(/\$\s?(\d+(?:\.\d+)?)/g)].map((m) => Number(m[1]));
}
