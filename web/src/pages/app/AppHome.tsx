import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getOuraStatus } from '../../lib/api';
import type { OuraStatus } from '../../types';

export function AppHome() {
  const [status, setStatus] = useState<OuraStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOuraStatus()
      .then(setStatus)
      .catch((err) => {
        console.error('Failed to get Oura status:', err);
        setError('Unable to check connection status');
        setStatus({ connected: false });
      })
      .finally(() => setLoading(false));
  }, []);

  const isConnected = status?.connected ?? false;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        Welcome to Oura Coach
      </h1>
      <p className="text-text-secondary mb-8">
        {isConnected
          ? 'Your Oura ring is connected. Explore your health insights below.'
          : 'Connect your Oura account to get started with personalized wellness insights.'}
      </p>

      {/* Loading state */}
      {loading && (
        <div className="bg-surface border border-border rounded-lg p-6 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span className="text-text-secondary">Checking connection status...</span>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="bg-surface border border-error/30 rounded-lg p-4 mb-6">
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      {/* Connect card - only show if not connected */}
      {!loading && !isConnected && (
        <div className="bg-surface border border-border rounded-lg p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-accent/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg
                className="w-6 h-6 text-accent"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold mb-1 text-text-primary">
                Connect Your Oura Ring
              </h2>
              <p className="text-sm text-text-secondary mb-4">
                Authorize Oura Coach to access your sleep, readiness, and activity
                data.
              </p>
              <Link
                to="/app/connect"
                className="inline-block px-6 py-3 bg-accent hover:bg-accent-hover text-background font-semibold rounded-lg transition-colors"
              >
                Connect Oura
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Connected status card */}
      {!loading && isConnected && (
        <div className="bg-surface border border-success/30 rounded-lg p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg
                className="w-6 h-6 text-success"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold mb-1 text-text-primary">
                Oura Connected
              </h2>
              <p className="text-sm text-text-secondary">
                Your Oura ring data is synced and ready to explore.
                {status?.sync_in_progress && (
                  <span className="text-accent ml-2">Syncing data...</span>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Insights card */}
        {isConnected ? (
          <Link
            to="/app/insights"
            className="bg-surface border border-border rounded-lg p-4 hover:border-accent transition-colors group"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold mb-1 text-text-primary group-hover:text-accent transition-colors">
                  Insights
                </h3>
                <p className="text-sm text-text-secondary">
                  View your health scores
                </p>
              </div>
              <svg
                className="w-5 h-5 text-text-muted group-hover:text-accent transition-colors"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </Link>
        ) : (
          <div className="bg-surface-elevated border border-border rounded-lg p-4 opacity-50 cursor-not-allowed">
            <h3 className="font-semibold mb-1 text-text-primary">Insights</h3>
            <p className="text-sm text-text-muted">
              Connect Oura first
            </p>
          </div>
        )}

        {/* Chat card */}
        <Link
          to="/app/chat"
          className="bg-surface border border-border rounded-lg p-4 hover:border-accent transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold mb-1 text-text-primary group-hover:text-accent transition-colors">
                Chat with Oura Coach
              </h3>
              <p className="text-sm text-text-secondary">
                Ask questions and get non-medical experiment ideas
              </p>
            </div>
            <svg
              className="w-5 h-5 text-text-muted group-hover:text-accent transition-colors"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </Link>

        {/* Experiments card */}
        <Link
          to="/app/experiments"
          className="bg-surface border border-border rounded-lg p-4 hover:border-accent transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold mb-1 text-text-primary group-hover:text-accent transition-colors">
                Experiments
              </h3>
              <p className="text-sm text-text-secondary">
                Review and chat about active experiments
              </p>
            </div>
            <svg
              className="w-5 h-5 text-text-muted group-hover:text-accent transition-colors"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </Link>
      </div>

      {/* Disclaimer */}
      <div className="mt-8 p-4 bg-surface-elevated rounded-lg border border-border">
        <p className="text-xs text-text-muted">
          <strong className="text-text-secondary">Reminder:</strong> Oura Coach
          provides wellness insights for informational purposes only. It is not
          a medical device and does not provide medical advice, diagnosis, or
          treatment. Always consult a healthcare professional for medical
          concerns.
        </p>
      </div>
    </div>
  );
}
