"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import type { UserRole, PlatformInfo } from "@/types/api";

interface AuthContextType {
  isAuthenticated: boolean;
  role: UserRole | null;
  platform: PlatformInfo | null;
  token: string;
  login: (token: string, role: UserRole, platform?: PlatformInfo) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  role: null,
  platform: null,
  token: "",
  login: () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState("");
  const [role, setRole] = useState<UserRole | null>(null);
  const [platform, setPlatform] = useState<PlatformInfo | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    const storedRole = localStorage.getItem("auth_role") as UserRole | null;
    const storedPlatform = localStorage.getItem("auth_platform");

    if (storedToken && storedRole) {
      setToken(storedToken);
      setRole(storedRole);
      apiClient.setToken(storedToken);
      setIsAuthenticated(true);

      if (storedPlatform) {
        try {
          setPlatform(JSON.parse(storedPlatform));
        } catch {
          // ignore parse error
        }
      }
    }
  }, []);

  const login = (newToken: string, newRole: UserRole, newPlatform?: PlatformInfo) => {
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("auth_role", newRole);
    if (newPlatform) {
      localStorage.setItem("auth_platform", JSON.stringify(newPlatform));
    } else {
      localStorage.removeItem("auth_platform");
    }

    apiClient.setToken(newToken);
    setToken(newToken);
    setRole(newRole);
    setPlatform(newPlatform || null);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_role");
    localStorage.removeItem("auth_platform");
    apiClient.setToken("");
    setToken("");
    setRole(null);
    setPlatform(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, platform, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
