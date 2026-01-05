import type { OAuthStartResponse, OuraStatus, OuraRawResponse, User, GoogleAuthStartResponse } from '../types';
import { getStoredToken } from './auth';

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8000';

/**
 * Fetch wrapper that adds authorization header if token exists
 */
async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getStoredToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  return fetch(url, {
    ...options,
    headers,
  });
}

// =============================================================================
// Google Auth API
// =============================================================================

/**
 * Start Google OAuth login flow
 */
export async function startGoogleLogin(): Promise<GoogleAuthStartResponse> {
  const response = await fetch(`${BACKEND_BASE_URL}/auth/google/start`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to start Google login: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get current authenticated user info
 */
export async function getCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${BACKEND_BASE_URL}/auth/me`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to get user: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// =============================================================================
// Oura OAuth API
// =============================================================================

/**
 * Start Oura OAuth connection flow
 * Requires authentication - user must be logged in first
 */
export async function startOuraConnect(): Promise<OAuthStartResponse> {
  const response = await authFetch(`${BACKEND_BASE_URL}/oura/connect/start`, {
    method: 'GET',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Please log in first to connect Oura');
    }
    throw new Error(`Failed to start OAuth: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get Oura connection status
 * Returns whether user is connected and cached data counts
 */
export async function getOuraStatus(): Promise<OuraStatus> {
  const response = await authFetch(`${BACKEND_BASE_URL}/oura/status`, {
    method: 'GET',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to get status: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch raw Oura data for a specific endpoint
 * @param endpoint - The Oura endpoint (e.g., 'daily_sleep', 'daily_readiness', 'daily_activity')
 * @param days - Number of days to fetch (default: 60)
 */
export async function getOuraRaw(endpoint: string, days: number = 60): Promise<OuraRawResponse> {
  const response = await authFetch(
    `${BACKEND_BASE_URL}/oura/raw?endpoint=${endpoint}&days=${days}`,
    {
      method: 'GET',
    }
  );

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to fetch ${endpoint}: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Disconnect Oura account
 * Removes stored OAuth tokens from the backend
 */
export async function disconnectOura(): Promise<{ success: boolean; message: string }> {
  const response = await authFetch(`${BACKEND_BASE_URL}/oura/disconnect`, {
    method: 'POST',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to disconnect: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
