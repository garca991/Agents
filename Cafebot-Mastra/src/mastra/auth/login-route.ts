import { registerApiRoute } from '@mastra/core/server';
import { signJwt } from './token.ts';

// Usuarios DEMO (en producción esto vendría de tu base de datos / IdP).
const USERS: Record<string, string> = {
  'juan-carlos': 'cafe123',
  'ana-lopez': 'cafe123',
};

// Ruta pública de login: valida usuario/contraseña y devuelve un JWT firmado.
export const loginRoute = registerApiRoute('/login', {
  method: 'POST',
  requiresAuth: false,
  handler: async (c) => {
    const body = (await c.req.json().catch(() => ({}))) as {
      username?: string;
      password?: string;
    };
    const username = (body.username ?? '').trim();
    const password = body.password ?? '';

    if (!username || USERS[username] !== password) {
      return c.json({ error: 'Credenciales inválidas' }, 401);
    }

    const secret = process.env.MASTRA_JWT_SECRET;
    if (!secret) {
      return c.json({ error: 'Auth no configurada en el servidor' }, 500);
    }

    const token = signJwt(
      { sub: username, name: username, iat: Math.floor(Date.now() / 1000) },
      secret,
    );
    return c.json({ token, user: { id: username, name: username } });
  },
});
