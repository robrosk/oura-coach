/**
 * Authentication utilities for JWT token management
 */

const TOKEN_KEY = 'oura_coach_token';

/**
 * Get the stored JWT token from localStorage
 */
export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Store JWT token in localStorage
 */
export function setStoredToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch (e) {
    console.error('Failed to store token:', e);
  }
}

/**
 * Clear the stored JWT token
 */
export function clearStoredToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch (e) {
    console.error('Failed to clear token:', e);
  }
}

/**
 * Decode a JWT token payload (without verification)
 * Only used client-side to check expiry
 */
export function decodeToken(token: string): { sub: string; email: string; exp: number } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch {
    return null;
  }
}

/**
 * Check if a JWT token is expired
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeToken(token);
  if (!payload || !payload.exp) return true;

  // Add 60 second buffer
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now + 60;
}

/**
 * Check if user is authenticated (has valid token)
 */
export function isAuthenticated(): boolean {
  const token = getStoredToken();
  if (!token) return false;
  return !isTokenExpired(token);
}
