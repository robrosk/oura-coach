import { useState } from 'react';
import { Link } from 'react-router-dom';
import { startOuraConnect } from '../../lib/api';

type ConnectionState = 'idle' | 'loading' | 'error';

export function Connect() {
  const [state, setState] = useState<ConnectionState>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    setState('loading');
    setError(null);

    try {
      const response = await startOuraConnect();
      // Redirect to Oura authorization page
      window.location.href = response.auth_url;
    } catch (err) {
      setState('error');
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to start connection. Please try again.'
      );
    }
  };

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <Link
        to="/app"
        className="inline-flex items-center gap-2 text-sm text-text-secondary hover:text-accent transition-colors mb-6"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to App
      </Link>

      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        Connect Oura Ring
      </h1>
      <p className="text-text-secondary mb-8">
        Authorize Oura Coach to securely access your Oura data. You can revoke
        access at any time from your Oura account settings.
      </p>

      {/* Connection card */}
      <div className="bg-surface border border-border rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 text-text-primary">
          What we'll access:
        </h2>
        <ul className="space-y-3 mb-6">
          <li className="flex items-start gap-3">
            <span className="text-accent mt-0.5">✓</span>
            <span className="text-text-secondary">
              Sleep data (duration, stages, efficiency)
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-accent mt-0.5">✓</span>
            <span className="text-text-secondary">
              Readiness scores and contributors
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-accent mt-0.5">✓</span>
            <span className="text-text-secondary">
              Activity data and goals
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-accent mt-0.5">✓</span>
            <span className="text-text-secondary">
              Basic profile information
            </span>
          </li>
        </ul>

        <button
          onClick={handleConnect}
          disabled={state === 'loading'}
          className={`w-full px-6 py-4 rounded-lg font-semibold transition-colors ${
            state === 'loading'
              ? 'bg-surface-elevated text-text-muted cursor-wait'
              : 'bg-accent hover:bg-accent-hover text-background cursor-pointer'
          }`}
        >
          {state === 'loading' ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Connecting...
            </span>
          ) : (
            'Connect with Oura'
          )}
        </button>

        {error && (
          <div className="mt-4 p-3 bg-error/10 border border-error/30 rounded-lg">
            <p className="text-sm text-error">{error}</p>
            <p className="text-xs text-text-muted mt-1">
              Make sure the backend server is running at the configured URL.
            </p>
          </div>
        )}
      </div>

      {/* Security note */}
      <div className="bg-surface-elevated border border-border rounded-lg p-4">
        <h3 className="font-semibold text-sm mb-2 text-text-primary">
          Security Note
        </h3>
        <p className="text-xs text-text-muted">
          Your OAuth tokens are stored securely on our backend. The mobile app
          never stores your Oura credentials or tokens directly. You can revoke
          access at any time through the Oura app or website.
        </p>
      </div>
    </div>
  );
}
