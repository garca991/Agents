import { useEffect, useMemo, useRef, useState } from 'react';
import { MastraClient } from '@mastra/client-js';
import { MASTRA_URL } from './config';

type Msg = { role: 'user' | 'assistant'; text: string };

// Lee el `sub` (usuario) del payload del JWT, solo para mostrarlo.
function jwtSub(token: string): string {
  try {
    const payload = JSON.parse(atob(token.split('.')[1] ?? '')) as { sub?: string };
    return payload.sub ?? '';
  } catch {
    return '';
  }
}

function getOrCreate(key: string, make: () => string): string {
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const value = make();
  localStorage.setItem(key, value);
  return value;
}

export default function Chat({ token, onLogout }: { token: string; onLogout: () => void }) {
  const client = useMemo(
    () => new MastraClient({ baseUrl: MASTRA_URL, headers: { Authorization: `Bearer ${token}` } }),
    [token],
  );

  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  const usuario = jwtSub(token);

  useEffect(() => {
    setThreadId(getOrCreate('cafebot.threadId', () => crypto.randomUUID()));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || loading || !threadId) return;
    setInput('');
    setLoading(true);
    setMessages((m) => [...m, { role: 'user', text }, { role: 'assistant', text: '' }]);

    try {
      const agent = client.getAgent('cafebot-agent');
      // resourceId lo deriva el servidor del usuario autenticado (mapUserToResourceId).
      const res = await agent.stream([{ role: 'user', content: text }], {
        memory: { thread: threadId },
      });
      await res.processDataStream({
        onChunk: (chunk) => {
          if (chunk.type === 'text-delta') {
            const delta = chunk.payload.text;
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = { ...last, text: last.text + delta };
              return copy;
            });
          }
        },
      });
    } catch (err) {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: 'assistant', text: '⚠️ Error: ' + String(err) };
        return copy;
      });
    } finally {
      setLoading(false);
    }
  }

  function newConversation() {
    const t = crypto.randomUUID();
    localStorage.setItem('cafebot.threadId', t);
    setThreadId(t);
    setMessages([]);
  }

  return (
    <div className="app">
      <header className="header">
        <h1>☕ CaféBot</h1>
        <div className="meta">
          <span title="usuario autenticado (resourceId de memoria)">usuario: {usuario || '—'}</span>
          <span title="conversación">thread: {threadId.slice(0, 8)}</span>
          <button onClick={newConversation}>Nueva conversación</button>
          <button onClick={onLogout}>Salir</button>
        </div>
      </header>

      <main className="chat">
        {messages.length === 0 && (
          <p className="hint">Pregúntame por cafés, pedidos, recetas o curiosidades del café.</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text || (loading && i === messages.length - 1 ? '…' : '')}
          </div>
        ))}
        <div ref={bottomRef} />
      </main>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu mensaje…"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? 'Enviando…' : 'Enviar'}
        </button>
      </form>
    </div>
  );
}
