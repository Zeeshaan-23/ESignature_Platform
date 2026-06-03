// src/context/AuthContext.jsx

import { createContext, useContext, useState, useEffect } from 'react';
import { getMe } from '../api/auth';
import api from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Runs ONCE on mount — restores session from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');

    if (!storedToken) {
      setLoading(false);
      return;
    }

    // Restore axios header immediately so getMe() is authenticated
    api.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
    setToken(storedToken);

    getMe()
      .then((res) => setUser(res.data))
      .catch(() => {
        // Token expired or invalid — wipe everything
        localStorage.removeItem('access_token');
        delete api.defaults.headers.common['Authorization'];
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, []); // Empty deps = mount only, never re-runs

  const login = (accessToken, refreshToken) => {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
  api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
  setToken(accessToken);
  getMe().then((res) => setUser(res.data));
};

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    delete api.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);