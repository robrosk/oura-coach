/**
 * Oura API types for frontend data display
 */

export interface OuraStatus {
  connected: boolean;
  user_id?: string;
  token_expires_at?: string;
  scopes?: string;
  cached_data_counts?: Record<string, number>;
  sync_in_progress?: boolean;
}

export interface OuraRawResponse {
  endpoint: string;
  count: number;
  items: OuraDailyRecord[];
}

export interface OuraDailyRecord {
  id: string;
  day: string; // YYYY-MM-DD
  score: number;
  // Additional fields that may be present
  timestamp?: string;
  contributors?: Record<string, number>;
}

export interface MetricStats {
  min: number;
  max: number;
  avg: number;
  count: number;
}

export interface WeeklyTrend {
  weekStart: string; // YYYY-MM-DD (Monday of the week)
  weekLabel: string; // e.g., "Dec 30 - Jan 5"
  avg: number;
  count: number;
}

export type MetricType = 'sleep' | 'readiness' | 'activity';

export interface MetricConfig {
  name: string;
  endpoint: string;
  icon: string;
  description: string;
}

export const METRIC_CONFIGS: Record<MetricType, MetricConfig> = {
  sleep: {
    name: 'Sleep',
    endpoint: 'daily_sleep',
    icon: 'moon',
    description: 'Your sleep quality and duration',
  },
  readiness: {
    name: 'Readiness',
    endpoint: 'daily_readiness',
    icon: 'battery',
    description: 'How ready your body is to perform',
  },
  activity: {
    name: 'Activity',
    endpoint: 'daily_activity',
    icon: 'activity',
    description: 'Your daily movement and exercise',
  },
};
