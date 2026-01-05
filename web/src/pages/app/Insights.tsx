import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getOuraRaw } from '../../lib/api';
import { computeStats, getScoreColor } from '../../lib/oura';
import type { MetricStats, MetricType } from '../../types';
import { METRIC_CONFIGS } from '../../types';

interface MetricData {
  stats: MetricStats;
  loading: boolean;
  error: string | null;
}

const METRICS: MetricType[] = ['sleep', 'readiness', 'activity'];

// Icons for each metric
const MetricIcon = ({ type, className }: { type: MetricType; className?: string }) => {
  switch (type) {
    case 'sleep':
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      );
    case 'readiness':
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
      );
    case 'activity':
      return (
        <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
          />
        </svg>
      );
  }
};

export function Insights() {
  const [data, setData] = useState<Record<MetricType, MetricData>>({
    sleep: { stats: { min: 0, max: 0, avg: 0, count: 0 }, loading: true, error: null },
    readiness: { stats: { min: 0, max: 0, avg: 0, count: 0 }, loading: true, error: null },
    activity: { stats: { min: 0, max: 0, avg: 0, count: 0 }, loading: true, error: null },
  });

  useEffect(() => {
    // Fetch all metrics in parallel
    METRICS.forEach(async (metric) => {
      const config = METRIC_CONFIGS[metric];
      try {
        const response = await getOuraRaw(config.endpoint, 61);
        const stats = computeStats(response.items);
        setData((prev) => ({
          ...prev,
          [metric]: { stats, loading: false, error: null },
        }));
      } catch (err) {
        console.error(`Failed to fetch ${metric}:`, err);
        setData((prev) => ({
          ...prev,
          [metric]: {
            ...prev[metric],
            loading: false,
            error: `Failed to load ${config.name.toLowerCase()} data`,
          },
        }));
      }
    });
  }, []);

  const allLoading = METRICS.every((m) => data[m].loading);

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        to="/app"
        className="inline-flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors mb-6"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Home
      </Link>

      {/* Header */}
      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        Your Health Insights
      </h1>
      <p className="text-text-secondary mb-8">
        60-day overview of your Oura data. Tap a card to see details.
      </p>

      {/* Loading skeleton */}
      {allLoading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {METRICS.map((metric) => (
            <div
              key={metric}
              className="bg-surface border border-border rounded-lg p-6 animate-pulse"
            >
              <div className="h-10 w-10 bg-surface-elevated rounded-lg mb-4" />
              <div className="h-4 w-20 bg-surface-elevated rounded mb-2" />
              <div className="h-8 w-16 bg-surface-elevated rounded mb-2" />
              <div className="h-3 w-24 bg-surface-elevated rounded" />
            </div>
          ))}
        </div>
      )}

      {/* Metric cards */}
      {!allLoading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {METRICS.map((metric) => {
            const config = METRIC_CONFIGS[metric];
            const metricData = data[metric];
            const hasData = metricData.stats.count > 0;

            return (
              <Link
                key={metric}
                to={`/app/insights/${metric}`}
                className="bg-surface border border-border rounded-lg p-6 hover:border-accent transition-colors group"
              >
                {/* Icon */}
                <div className="w-10 h-10 bg-accent/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-accent/20 transition-colors">
                  <MetricIcon type={metric} className="w-5 h-5 text-accent" />
                </div>

                {/* Title */}
                <h3 className="font-semibold text-text-primary group-hover:text-accent transition-colors mb-1">
                  {config.name}
                </h3>

                {/* Score or error */}
                {metricData.error ? (
                  <p className="text-sm text-error">{metricData.error}</p>
                ) : metricData.loading ? (
                  <div className="h-8 w-16 bg-surface-elevated rounded animate-pulse" />
                ) : hasData ? (
                  <>
                    <div className="flex items-baseline gap-2 mb-1">
                      <span
                        className={`text-3xl font-bold ${getScoreColor(metricData.stats.avg)}`}
                      >
                        {metricData.stats.avg}
                      </span>
                      <span className="text-sm text-text-muted">avg</span>
                    </div>
                    <p className="text-xs text-text-muted">
                      {metricData.stats.count} days of data
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-text-muted">No data available</p>
                )}

                {/* Arrow */}
                <div className="mt-4 flex justify-end">
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
            );
          })}
        </div>
      )}

      {/* Info note */}
      <div className="mt-8 p-4 bg-surface-elevated rounded-lg border border-border">
        <p className="text-xs text-text-muted">
          Scores range from 0-100. Higher scores indicate better performance.
          Data is automatically synced from your Oura ring.
        </p>
      </div>
    </div>
  );
}
