import type {
  OAuthStartResponse,
  OuraStatus,
  OuraRawResponse,
  User,
  GoogleAuthStartResponse,
  ChatMessage,
  ChatResponse,
  ChatStreamEvent,
  Experiment,
  ExperimentListResponse,
} from '../types';
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

// =============================================================================
// Agent Chat API
// =============================================================================

/**
 * Send a chat message to the backend agent
 */
export async function sendChatMessage(
  message: string,
  history: ChatMessage[] = []
): Promise<ChatResponse> {
  const response = await authFetch(`${BACKEND_BASE_URL}/agent/chat`, {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to send message: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Stream a chat response from the backend agent as NDJSON events.
 */
export async function* streamChatMessage(
  message: string,
  history: ChatMessage[] = []
): AsyncGenerator<ChatStreamEvent> {
  const response = await authFetch(`${BACKEND_BASE_URL}/agent/chat/stream`, {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to stream message: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Streaming response is not supported in this browser.');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newlineIndex = buffer.indexOf('\n');
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) {
        try {
          yield JSON.parse(line) as ChatStreamEvent;
        } catch (err) {
          console.warn('Failed to parse stream event:', err);
        }
      }
      newlineIndex = buffer.indexOf('\n');
    }
  }

  const remaining = buffer.trim();
  if (remaining) {
    try {
      yield JSON.parse(remaining) as ChatStreamEvent;
    } catch (err) {
      console.warn('Failed to parse final stream event:', err);
    }
  }
}

// =============================================================================
// Experiments API
// =============================================================================

export async function listExperiments(): Promise<ExperimentListResponse> {
  const response = await authFetch(`${BACKEND_BASE_URL}/experiments`, {
    method: 'GET',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to fetch experiments: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function getExperiment(experimentId: string): Promise<Experiment> {
  const response = await authFetch(`${BACKEND_BASE_URL}/experiments/${experimentId}`, {
    method: 'GET',
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to fetch experiment: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function* streamExperimentChat(
  experimentId: string,
  message: string,
  history: ChatMessage[] = []
): AsyncGenerator<ChatStreamEvent> {
  const response = await authFetch(`${BACKEND_BASE_URL}/agent/experiments/${experimentId}/chat/stream`, {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to stream message: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Streaming response is not supported in this browser.');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newlineIndex = buffer.indexOf('\n');
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) {
        try {
          yield JSON.parse(line) as ChatStreamEvent;
        } catch (err) {
          console.warn('Failed to parse stream event:', err);
        }
      }
      newlineIndex = buffer.indexOf('\n');
    }
  }

  const remaining = buffer.trim();
  if (remaining) {
    try {
      yield JSON.parse(remaining) as ChatStreamEvent;
    } catch (err) {
      console.warn('Failed to parse final stream event:', err);
    }
  }
}
