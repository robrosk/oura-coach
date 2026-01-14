import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listExperiments } from '../../lib/api';
import type { Experiment } from '../../types';

const STATUS_STYLES: Record<string, { badge: string; text: string }> = {
  active: { badge: 'bg-success/15 text-success', text: 'Active' },
  ended: { badge: 'bg-surface-elevated text-text-secondary', text: 'Ended' },
  success: { badge: 'bg-success/20 text-success', text: 'Success' },
  failure: { badge: 'bg-error/15 text-error', text: 'Failed' },
};

function getStatusStyle(status: string) {
  return STATUS_STYLES[status] || { badge: 'bg-surface-elevated text-text-secondary', text: status };
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

      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">Experiments</h1>
      <p className="text-text-secondary mb-6">
        Track your current experiments and review what you are testing.
      </p>

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
        <div className="bg-surface border border-border rounded-lg p-6 text-sm text-text-secondary">
          No experiments yet. Ask Oura Coach to create one for you.
        </div>
      )}

      <div className="space-y-4">
        {experiments.map((experiment) => {
          const status = getStatusStyle(experiment.status);
          return (
            <div
              key={experiment.id}
              className="bg-surface border border-border rounded-lg p-5 hover:border-accent transition-colors"
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">
                    {experiment.title}
                  </h2>
                  <p className="text-sm text-text-secondary mt-1">
                    {experiment.objective}
                  </p>
                </div>
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${status.badge}`}>
                  {status.text}
                </span>
              </div>
              <div className="mt-3 text-xs text-text-muted flex flex-wrap gap-3">
                <span>Start: {experiment.start_date}</span>
                <span>End: {experiment.end_date}</span>
                <span>{experiment.duration_days} days</span>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <div className="text-xs text-text-secondary">
                  Success criteria: {experiment.success_criteria}
                </div>
                <Link
                  to={`/app/experiments/${experiment.id}`}
                  className="text-sm font-semibold text-accent hover:text-accent-hover"
                >
                  Open Chat
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
