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
  id?: string;
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

export interface Experiment {
  id: string;
  title: string;
  objective: string;
  hypothesis: string;
  protocol: string;
  duration_days: number;
  start_date: string;
  end_date: string;
  status: string;
  success_criteria: string;
  metrics: string[];
  outcome?: string | null;
}

export interface ExperimentListResponse {
  experiments: Experiment[];
}

export type ChatStreamEvent =
  | { type: 'token'; content: string }
  | { type: 'tool_start'; tool_call: ToolCall }
  | { type: 'tool_end'; tool_call_id: string; resolved_range?: ToolCall['resolved_range'] }
  | { type: 'done'; reply: string; tool_calls?: ToolCall[] }
  | { type: 'error'; message: string };

// Re-export Oura types
export * from './oura';

// Re-export Auth types
export * from './auth';
