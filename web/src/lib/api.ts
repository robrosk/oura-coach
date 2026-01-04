import type { OAuthStartResponse } from '../types';

const BACKEND_BASE_URL = import.meta.env.VITE_BACKEND_BASE_URL || 'http://localhost:8000';

/**
 * Start Oura OAuth connection flow
 * Calls backend to get authorization URL
 */
export async function startOuraConnect(): Promise<OAuthStartResponse> {
  const response = await fetch(`${BACKEND_BASE_URL}/oura/connect/start`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to start OAuth: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
