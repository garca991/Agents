import { useEffect, useState } from 'react';
import Login from './Login';
import Chat from './Chat';
import './App.css';

export default function App() {
  const [token, setToken] = useState<string | null>(null);

  // Al cargar, recupera el token guardado (si lo hay).
  useEffect(() => {
    setToken(localStorage.getItem('cafebot.jwt'));
  }, []);

  function handleLogin(t: string) {
    localStorage.setItem('cafebot.jwt', t);
    setToken(t);
  }

  function handleLogout() {
    localStorage.removeItem('cafebot.jwt');
    setToken(null);
  }

  return token ? (
    <Chat token={token} onLogout={handleLogout} />
  ) : (
    <Login onLogin={handleLogin} />
  );
}
