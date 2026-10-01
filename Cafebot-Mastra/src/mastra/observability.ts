import { Observability, MastraStorageExporter } from '@mastra/observability';

// Observabilidad: registra trazas jerárquicas (agente → modelo, tools, MCP,
// workflows y processors) y las persiste en el storage de Mastra (cafebot.db)
// para poder consultarlas desde Studio (playground) o por SQL.
export const cafeObservability = new Observability({
  configs: {
    default: {
      serviceName: 'cafebot',
      exporters: [new MastraStorageExporter()],
    },
  },
});