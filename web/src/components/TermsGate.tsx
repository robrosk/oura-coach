import { Navigate, useLocation } from 'react-router-dom';
import { isTermsAccepted } from '../lib/terms';

interface TermsGateProps {
  children: React.ReactNode;
}

/**
 * Wrapper component that redirects to /accept if terms not accepted
 * Passes the intended destination as state so we can redirect back after acceptance
 */
export function TermsGate({ children }: TermsGateProps) {
  const location = useLocation();

  if (!isTermsAccepted()) {
    // Redirect to accept page, preserving the intended destination
    return (
      <Navigate
        to="/accept"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  }

  return <>{children}</>;
}
