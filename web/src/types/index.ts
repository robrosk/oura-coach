export interface TermsAcceptance {
  termsAccepted: boolean;
  privacyAcknowledged: boolean;
  termsAcceptedAt: string; // ISO timestamp
  termsVersion: string;
}

export interface OAuthStartResponse {
  auth_url: string;
  state?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  resolved_range?: {
    days?: number;
    start_date?: string;
    end_date?: string;
  };
}

export interface ChatResponse {
  reply: string;
  tool_calls?: ToolCall[];
}

// Re-export Oura types
export * from './oura';

// Re-export Auth types
export * from './auth';
