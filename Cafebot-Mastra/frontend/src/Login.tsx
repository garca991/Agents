import { useState } from 'react';
import { MASTRA_URL } from './config';

type Props = { onLogin: (token: string) => void };

export default function Login({ onLogin }: Props) {
  const [username, setUsername] = useState('juan-carlos');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${MASTRA_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = (await res.json()) as { token?: string; error?: string };
      if (!res.ok || !data.token) throw new Error(data.error ?? 'Error de login');
      onLogin(data.token);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <h1>☕ CaféBot</h1>
        <p className="sub">Inicia sesión para chatear</p>

        <label>
          Usuario
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            placeholder="cafe123"
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={loading || !username || !password}>
          {loading ? 'Entrando…' : 'Entrar'}
        </button>

        <p className="hint-users">
          Usuarios demo: <code>juan-carlos</code> o <code>ana-lopez</code> · contraseña <code>cafe123</code>
        </p>
      </form>
    </div>
  );
}
