import { Mastra } from '@mastra/core';
import { MastraJwtAuth } from '@mastra/auth';
import { cafebotAgent } from './agents/cafebot-agent.ts';
import { orderWorkflow } from './workflows/order-workflow.ts';
import { cafeStorage } from './storage.ts';
import { cafeObservability } from './observability.ts';
import { loginRoute } from './auth/login-route.ts';

export const mastra = new Mastra({
  agents: { cafebotAgent },
  workflows: { orderWorkflow },
  storage: cafeStorage,
  observability: cafeObservability,
  server: {
    // CORS: permite que el frontend (Vite en localhost:5173) llame al server.
    cors: { origin: '*' },
    // Auth por JWT: exige `Authorization: Bearer <token>` en /api/*.
    // El `sub` del token se usa como resourceId de la memoria.
    auth: new MastraJwtAuth({
      secret: process.env.MASTRA_JWT_SECRET,
      mapUserToResourceId: (user) => String(user.sub ?? ''),
    }),
    // Ruta pública de login (no requiere token).
    apiRoutes: [loginRoute],
  },
});
