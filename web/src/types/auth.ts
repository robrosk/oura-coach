/**
 * Authentication types for Google OAuth and JWT
 */

export interface User {
  id: string;
  email: string;
  name?: string;
  picture?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export interface GoogleAuthStartResponse {
  auth_url: string;
  state: string;
}

export interface AuthContextValue extends AuthState {
  login: () => Promise<void>;
  logout: () => void;
  setAuthFromCallback: (token: string) => Promise<void>;
}
