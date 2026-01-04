import type { TermsAcceptance } from '../types';

const STORAGE_KEY = 'oura_coach_terms_acceptance';

/**
 * Get stored terms acceptance data
 */
export function getTermsAcceptance(): TermsAcceptance | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as TermsAcceptance;
  } catch {
    return null;
  }
}

/**
 * Store terms acceptance
 */
export function setTermsAcceptance(version: string): void {
  const acceptance: TermsAcceptance = {
    termsAccepted: true,
    privacyAcknowledged: true,
    termsAcceptedAt: new Date().toISOString(),
    termsVersion: version,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(acceptance));
}

/**
 * Clear terms acceptance (for testing/dev)
 */
export function clearTermsAcceptance(): void {
  localStorage.removeItem(STORAGE_KEY);
}
