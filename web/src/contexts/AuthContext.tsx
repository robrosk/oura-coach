import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import type { User, AuthContextValue } from '../types';
import {
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  isTokenExpired,
} from '../lib/auth';
import { startGoogleLogin, getCurrentUser } from '../lib/api';

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = getStoredToken();

      if (storedToken && !isTokenExpired(storedToken)) {
        try {
          const userData = await getCurrentUser(storedToken);
          setUser(userData);
          setToken(storedToken);
        } catch (err) {
          console.error('Failed to fetch user:', err);
          clearStoredToken();
        }
      } else if (storedToken) {
        // Token expired, clear it
        clearStoredToken();
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async () => {
    try {
      const { auth_url } = await startGoogleLogin();
      // Redirect to Google OAuth
      window.location.href = auth_url;
    } catch (err) {
      console.error('Failed to start login:', err);
      throw err;
    }
  };

  const logout = () => {
    clearStoredToken();
    setUser(null);
    setToken(null);
    // Redirect to login page
    window.location.href = '/login';
  };

  const setAuthFromCallback = async (newToken: string) => {
    setStoredToken(newToken);
    setToken(newToken);

    try {
      const userData = await getCurrentUser(newToken);
      setUser(userData);
    } catch (err) {
      console.error('Failed to fetch user after login:', err);
      clearStoredToken();
      setToken(null);
      throw err;
    }
  };

  const value: AuthContextValue = {
    user,
    token,
    isLoading,
    isAuthenticated: !!user && !!token,
    login,
    logout,
    setAuthFromCallback,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
