import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { isTermsAccepted } from '../lib/terms';
import { setNextPath } from '../lib/routes';

interface TermsGateProps {
  children: React.ReactNode;
}

/**
 * Wrapper component that redirects to /accept if terms not accepted
 * Passes the intended destination as state so we can redirect back after acceptance
 */
export function TermsGate({ children }: TermsGateProps) {
  const location = useLocation();
  const nextPath = `${location.pathname}${location.search}`;
  const needsAcceptance = !isTermsAccepted();

  useEffect(() => {
    if (needsAcceptance) {
      setNextPath(nextPath);
    }
  }, [needsAcceptance, nextPath]);

  if (needsAcceptance) {
    // Redirect to accept page, preserving the intended destination
    return (
      <Navigate
        to={`/accept?next=${encodeURIComponent(nextPath)}`}
        replace
      />
    );
  }

  return <>{children}</>;
}
