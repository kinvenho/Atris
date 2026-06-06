export type RecommendationEvidence = {
  id: string;
  recommendation_id: string;
  source_url: string;
  summary: string;
  retrieved_at: string;
};

export type Recommendation = {
  id: string;
  market_id: string | null;
  market_question: string;
  side: "YES" | "NO";
  market_probability: number;
  atris_probability: number;
  edge: number;
  confidence: number;
  reasoning: string;
  evidence_summary: string;
  status: "active" | "resolved" | "expired";
  result: "correct" | "incorrect" | "pending";
  created_at: string;
  resolved_at?: string | null;
  evidence?: RecommendationEvidence[];
};

export type PerformanceSnapshot = {
  id?: string;
  snapshot_at: string | null;
  total_predictions: number;
  correct: number;
  incorrect: number;
  pending: number;
  accuracy_rate: number;
  average_edge: number;
};

export type AgentRun = {
  id: string;
  started_at: string;
  completed_at: string | null;
  markets_scanned: number;
  candidates_evaluated: number;
  recommendations_published: number;
  errors: unknown[];
  status: "success" | "partial" | "failed";
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, fallback: T, timeoutMs = 8000): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      return fallback;
    }

    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export function formatPercent(value: number, precision = 1) {
  return `${(Number(value || 0) * 100).toFixed(precision)}%`;
}

export function formatSignedPercent(value: number) {
  const amount = Number(value || 0) * 100;
  const sign = amount > 0 ? "+" : "";
  return `${sign}${amount.toFixed(1)}%`;
}

export function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function getRecommendations() {
  return getJson<Recommendation[]>("/recommendations", []);
}

export function getRecommendation(id: string) {
  return getJson<Recommendation | null>(`/recommendations/${id}`, null);
}

export function getPerformance() {
  return getJson<PerformanceSnapshot>("/performance", {
    snapshot_at: null,
    total_predictions: 0,
    correct: 0,
    incorrect: 0,
    pending: 0,
    accuracy_rate: 0,
    average_edge: 0,
  });
}

export function getAgentRuns() {
  return getJson<AgentRun[]>("/agent/runs", []);
}

export type F1Prediction = {
  driver_id: string;
  driver_code?: string | null;
  driver_number?: string | null;
  constructor_id?: string | null;
  constructor_name?: string | null;
  grid?: number | string | null;
  qualifying_position?: number | string | null;
  latest_position?: number | string | null;
  latest_lap_number?: number | string | null;
  points_finish_probability: number;
  podium_finish_probability: number;
  confidence?: number | null;
  features?: Record<string, unknown>;
};

export type F1PredictionBoard = {
  prediction_mode?: string;
  feature_set?: string;
  generated_at?: string | null;
  predictions: F1Prediction[];
  models?: Record<string, unknown>;
};

export type F1DashboardSession = {
  session_key: number;
  link?: {
    session_name?: string | null;
    session_type?: string | null;
    date_start?: string | null;
    race_name?: string | null;
  };
  events?: Array<Record<string, unknown>>;
  driver_snapshots?: Array<Record<string, unknown>>;
  feature_snapshots?: Array<Record<string, unknown>>;
  predictions?: F1PredictionBoard | null;
  freshness?: Record<string, unknown>;
};

export type F1DashboardPayload = {
  season: number;
  round: number;
  race?: {
    race_name?: string | null;
    circuit_name?: string | null;
    locality?: string | null;
    country?: string | null;
    race_date?: string | null;
    race_time?: string | null;
  } | null;
  sessions: F1DashboardSession[];
  pre_race_predictions?: F1PredictionBoard | null;
  latest_race_weekend_predictions?: F1PredictionBoard | null;
  freshness?: {
    built_at?: string | null;
    linked_sessions?: number;
    pre_race_prediction_count?: number;
    race_weekend_prediction_count?: number;
    latest_event_time?: string | null;
    latest_feature_snapshot_at?: string | null;
    latest_prediction_built_at?: string | null;
  };
};

export type F1RaceSummary = {
  season?: number;
  round?: number | string | null;
  race_name?: string | null;
  circuit_name?: string | null;
  locality?: string | null;
  country?: string | null;
  race_date?: string | null;
  race_time?: string | null;
  updated_at?: string | null;
};

export function getF1Dashboard(season: number, round: number) {
  return getJson<F1DashboardPayload | null>(
    `/f1/dashboard/seasons/${season}/rounds/${round}?event_limit=80`,
    null,
    2500,
  );
}

export function getF1StoredRaces(season: number) {
  return getJson<F1RaceSummary[]>(`/f1/stored/seasons/${season}/races?limit=100`, [], 2500);
}
