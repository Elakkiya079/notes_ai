import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);
  const [config, setConfig] = useState(null);
  const [error, setError] = useState('');

  async function refresh() {
    const [nextConfig, me] = await Promise.all([api('/api/auth/config'), api('/api/auth/me')]);
    setConfig(nextConfig);
    setUser(me.user);
    setError('');
  }

  useEffect(() => {
    refresh().catch(() => {
      setUser(null);
      setError('The notes server is not running.');
    });
  }, []);

  const value = useMemo(() => ({ user, setUser, config, error, refresh }), [user, config, error]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
