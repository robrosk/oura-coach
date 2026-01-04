import { getTermsAcceptance } from './storage';

// Update this version when Terms of Service changes materially
export const CURRENT_TERMS_VERSION = '2026-01-04';

/**
 * Check if the user has accepted the current version of Terms
 */
export function isTermsAccepted(): boolean {
  const acceptance = getTermsAcceptance();
  if (!acceptance) return false;

  return (
    acceptance.termsAccepted &&
    acceptance.privacyAcknowledged &&
    acceptance.termsVersion === CURRENT_TERMS_VERSION
  );
}
