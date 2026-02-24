"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { apiClient } from "@/lib/api";

interface AuthContextType {
  isAuthenticated: boolean;
  adminKey: string;
  login: (key: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  adminKey: "",
  login: () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [adminKey, setAdminKey] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("admin_api_key");
    if (stored) {
      setAdminKey(stored);
      apiClient.setAdminKey(stored);
      setIsAuthenticated(true);
    }
  }, []);

  const login = (key: string) => {
    localStorage.setItem("admin_api_key", key);
    apiClient.setAdminKey(key);
    setAdminKey(key);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem("admin_api_key");
    apiClient.setAdminKey("");
    setAdminKey("");
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, adminKey, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
