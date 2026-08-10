import React, { createContext, useContext, useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';

const AuthContext = createContext();

const API_BASE = API_BASE_URL;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load persisted token and user on mount
    try {
      const savedToken = localStorage.getItem('ai_interview_token');
      const savedUser = localStorage.getItem('ai_interview_user');
      if (savedToken && savedUser) {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      }
    } catch (e) {
      console.error('Error loading saved auth state:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (username, password) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Login failed');
    }
    setToken(data.token);
    setUser(data.user);
    localStorage.setItem('ai_interview_token', data.token);
    localStorage.setItem('ai_interview_user', JSON.stringify(data.user));
    return data.user;
  };

  const register = async (username, name, password) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, name, password })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Registration failed');
    }
    setToken(data.token);
    setUser(data.user);
    localStorage.setItem('ai_interview_token', data.token);
    localStorage.setItem('ai_interview_user', JSON.stringify(data.user));
    return data.user;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('ai_interview_token');
    localStorage.removeItem('ai_interview_user');
  };

  const fetchUserInterviews = async () => {
    if (!user?.username && !token) return [];
    try {
      const headers = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      const url = token 
        ? `${API_BASE}/api/user/interviews` 
        : `${API_BASE}/api/user/interviews?username=${encodeURIComponent(user.username)}`;

      const res = await fetch(url, { headers });
      const data = await res.json();
      return data.interviews || [];
    } catch (e) {
      console.error('Error fetching user interviews:', e);
      return [];
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      fetchUserInterviews
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
