'use client'

import { useCallback, useState, useEffect } from 'react'

interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  user: { name: string; email: string } | null
}

/**
 * Custom auth hook - placeholder for NextAuth/Keycloak integration
 * Will be enhanced with proper session management in production
 */
export function useAuth(): AuthState & { login: (email: string, password: string) => Promise<void>; logout: () => void } {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
  })

  useEffect(() => {
    // Check for stored token on mount
    const token = localStorage.getItem('access_token')
    if (token) {
      setState({
        isAuthenticated: true,
        isLoading: false,
        user: { name: 'Admin', email: 'admin@raas.local' },
      })
    } else {
      setState((prev) => ({ ...prev, isLoading: false }))
    }
  }, [])

  const login = useCallback(async (email: string, _password: string) => {
    // Placeholder - will integrate with backend auth
    localStorage.setItem('access_token', 'placeholder-token')
    setState({
      isAuthenticated: true,
      isLoading: false,
      user: { name: 'Admin', email },
    })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setState({
      isAuthenticated: false,
      isLoading: false,
      user: null,
    })
  }, [])

  return { ...state, login, logout }
}
