import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listExperiments } from '../../lib/api';
import type { Experiment } from '../../types';

const STATUS_STYLES: Record<
  string,
  { badge: string; text: string; border: string; dot: string }
> = {
  active: {
    badge: 'bg-success/15 text-success',
    text: 'Active',
    border: 'border-success/40',
    dot: 'bg-success',
  },
  ended: {
    badge: 'bg-surface-elevated text-text-secondary',
    text: 'Ended',
    border: 'border-border/60',
    dot: 'bg-text-muted',
  },
  success: {
    badge: 'bg-success/20 text-success',
    text: 'Success',
    border: 'border-success/40',
    dot: 'bg-success',
  },
  failure: {
    badge: 'bg-error/15 text-error',
    text: 'Failed',
    border: 'border-error/40',
    dot: 'bg-error',
  },
};

function getStatusStyle(status: string) {
  return (
    STATUS_STYLES[status] || {
      badge: 'bg-surface-elevated text-text-secondary',
      text: status,
      border: 'border-border/60',
      dot: 'bg-text-muted',
    }
  );
}

export function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listExperiments()
      .then((response) => setExperiments(response.experiments))
      .catch((err) => {
        console.error('Failed to load experiments:', err);
        setError('Unable to load experiments right now.');
      })
      .finally(() => setLoading(false));
  }, []);

  const activeCount = experiments.filter((experiment) => experiment.status === 'active').length;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link
        to="/app"
        className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Home
      </Link>

      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">Experiments</h1>
          <p className="text-text-secondary">
            Track what you are testing and keep notes in context.
          </p>
          {!loading && experiments.length > 0 && (
            <p className="text-xs text-text-muted mt-2">
              {experiments.length} total · {activeCount} active
            </p>
          )}
        </div>
        <Link
          to="/app/chat"
          className="inline-flex items-center justify-center gap-2 rounded-full border border-accent/40 px-4 py-2 text-sm font-semibold text-accent hover:bg-accent/10 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h8m-8 4h5m8-2a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          Create via Chat
        </Link>
      </div>

      {loading && (
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span className="text-text-secondary">Loading experiments...</span>
          </div>
        </div>
      )}

      {error && !loading && (
        <div className="bg-error/10 border border-error/30 rounded-lg p-3 mb-4">
          <p className="text-sm text-error">{error}</p>
        </div>
      )}

      {!loading && experiments.length === 0 && (
        <div className="bg-surface border border-border rounded-xl p-6 text-sm text-text-secondary">
          <p className="font-semibold text-text-primary mb-2">No experiments yet</p>
          <p className="text-text-secondary">
            Start by asking Oura Coach to draft a new experiment.
          </p>
          <Link
            to="/app/chat"
            className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-hover"
          >
            Open chat
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      )}

      <div className="space-y-4">
        {experiments.map((experiment) => {
          const status = getStatusStyle(experiment.status);
          return (
            <div
              key={experiment.id}
              className={`bg-surface border ${status.border} border-l-4 rounded-xl p-5 transition-colors`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${status.dot}`} />
                    <h2 className="text-lg font-semibold text-text-primary">
                      {experiment.title}
                    </h2>
                  </div>
                  <p className="text-sm text-text-secondary">{experiment.objective}</p>
                </div>
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${status.badge}`}>
                  {status.text}
                </span>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-text-muted">
                <span className="rounded-full bg-surface-elevated px-3 py-1">
                  Start {experiment.start_date}
                </span>
                <span className="rounded-full bg-surface-elevated px-3 py-1">
                  End {experiment.end_date}
                </span>
                <span className="rounded-full bg-surface-elevated px-3 py-1">
                  {experiment.duration_days} days
                </span>
              </div>
              <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="text-xs text-text-secondary">
                  Success criteria: <span className="text-text-primary">{experiment.success_criteria}</span>
                </div>
                <Link
                  to={`/app/experiments/${experiment.id}`}
                  className="inline-flex items-center gap-2 text-sm font-semibold text-accent hover:text-accent-hover"
                >
                  Open Chat
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </div>
              {experiment.outcome && (
                <div className="mt-4 rounded-lg bg-surface-elevated px-3 py-2 text-xs text-text-secondary">
                  Outcome: <span className="text-text-primary">{experiment.outcome}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
