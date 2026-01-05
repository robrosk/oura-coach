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

// Re-export Oura types
export * from './oura';

// Re-export Auth types
export * from './auth';
