// src/context/AuthContext.jsx

import { createContext, useContext, useState, useEffect } from 'react';
import { getMe, logoutUser } from '../api/auth';
import api from '../api/axios';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Runs ONCE on mount — restores session by checking if we have a valid cookie
  useEffect(() => {
    getMe()
      .then((res) => {
        setUser(res.data);
      })
      .catch(() => {
        // Not authenticated or token expired
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []); // Empty deps = mount only, never re-runs

  const login = (userData) => {
    setUser(userData);
  };

  const logout = async () => {
    try {
      await logoutUser();
    } catch (err) {
      console.error("Logout failed", err);
    } finally {
      setUser(null);
    }
  };

  // We consider the user authenticated if `user` is not null.
  // Instead of passing `token`, we can pass a boolean `isAuthenticated`.
  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);