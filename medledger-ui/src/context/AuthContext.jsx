// src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext();

// Tiny function to parse a JWT’s payload without extra deps
function parseJwt(token) {
  try {
    const base64 = token.split('.')[1];
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(
      decodeURIComponent(
        Array.prototype.map
          .call(json, (c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      )
    );
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  // On mount, load token & set axios header if present
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      const payload = parseJwt(token);
      if (payload) setUser({ name: payload.sub, role: payload.role });
    }
  }, []);

  // Login via FastAPI /users/token (OAuth2 password flow)
  async function login(username, password) {
    // Build x-www-form-urlencoded payload
    const body = new URLSearchParams({ username, password });

    // Must explicitly set this header so FastAPI reads form fields
    const resp = await api.post(
      '/users/token',
      body,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );

    const token = resp.data.access_token;
    // Persist token & configure axios for future calls
    localStorage.setItem('access_token', token);
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

    // Decode and populate user state
    const payload = parseJwt(token);
    setUser({ name: payload.sub, role: payload.role });
  }

  function logout() {
    localStorage.removeItem('access_token');
    delete api.defaults.headers.common['Authorization'];
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
