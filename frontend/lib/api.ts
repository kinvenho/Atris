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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://atris-production.up.railway.app";

async function getJson<T>(path: string, fallback: T, timeoutMs = 8000): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
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

export type F1SessionEvent = {
  id?: string;
  session_key: number;
  event_type?: string | null;
  event_time?: string | null;
  driver_number?: number | string | null;
  lap_number?: number | string | null;
  category?: string | null;
  flag?: string | null;
  scope?: string | null;
  message?: string | null;
  updated_at?: string | null;
};

export type F1DriverSessionSnapshot = {
  id?: string;
  session_key: number;
  driver_number: number | string;
  latest_position?: number | string | null;
  latest_lap_number?: number | string | null;
  fastest_lap_duration?: number | string | null;
  lap_count?: number | string | null;
  position_samples?: number | string | null;
  metrics?: Record<string, number | string | null | undefined>;
  updated_at?: string | null;
};

export type F1DashboardSession = {
  session_key: number;
  link?: {
    session_name?: string | null;
    session_type?: string | null;
    date_start?: string | null;
    race_name?: string | null;
    metadata?: {
      session_date_start?: string | null;
      session_location?: string | null;
      session_circuit_short_name?: string | null;
      race_country?: string | null;
      race_locality?: string | null;
      race_circuit_name?: string | null;
      race_date?: string | null;
    };
  };
  events?: F1SessionEvent[];
  driver_snapshots?: F1DriverSessionSnapshot[];
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

export type F1RaceResult = {
  season: number;
  round: number;
  race_name?: string | null;
  driver_id: string;
  driver_code?: string | null;
  driver_number?: number | string | null;
  constructor_id?: string | null;
  constructor_name?: string | null;
  grid?: number | null;
  position?: number | null;
  position_order?: number | null;
  position_text?: string | null;
  points?: number | null;
  laps?: number | null;
  status?: string | null;
  race_time?: string | null;
  fastest_lap_rank?: number | string | null;
  fastest_lap_time?: string | null;
  source_payload?: {
    Driver?: {
      url?: string | null;
    };
    Constructor?: {
      url?: string | null;
    };
  } | null;
};

export type F1QualifyingResult = {
  season: number;
  round: number;
  race_name?: string | null;
  driver_id: string;
  driver_code?: string | null;
  driver_number?: string | null;
  given_name?: string | null;
  family_name?: string | null;
  constructor_id?: string | null;
  constructor_name?: string | null;
  qualifying_position?: number | null;
  q1?: string | null;
  q2?: string | null;
  q3?: string | null;
};

export type F1SessionRaceLink = {
  session_key: number;
  season: number;
  round: number;
  race_name?: string | null;
  session_name?: string | null;
  session_type?: string | null;
  confidence?: number | null;
  match_reason?: string | null;
  metadata?: {
    session_date_start?: string | null;
    session_location?: string | null;
    session_circuit_short_name?: string | null;
    race_country?: string | null;
    race_locality?: string | null;
    race_circuit_name?: string | null;
    race_date?: string | null;
  };
};

export type F1ModelVersion = {
  id: string;
  model_name: string;
  outcome_type: string;
  version: string;
  status: "candidate" | "active" | "retired";
  training_window?: Record<string, unknown>;
  metrics?: {
    train?: Record<string, number>;
    eval?: Record<string, number>;
    trained_at?: string;
    train_examples?: number;
    eval_examples?: number;
  };
  created_at?: string;
};

export type F1BacktestPrediction = {
  season: number;
  round: number;
  race_name?: string | null;
  driver_id: string;
  driver_code?: string | null;
  constructor_name?: string | null;
  outcome_type: string;
  label?: boolean | null;
  probability: number;
  predicted_label?: boolean | null;
  feature_set?: string | null;
  split?: string | null;
};

export type F1DataSource = {
  name: string;
  kind: "historical" | "live" | "analysis" | "market";
  status: "ready" | "evaluating" | "roadmap";
  access: string;
  role: string;
  notes: string;
  url: string;
};

export type F1LiveReadiness = {
  historical_first: boolean;
  preferred_live_path: string;
  supabase_storage_policy: string;
  live_options: F1DataSource[];
};

export type F1DataCoverage = {
  season: number;
  races: number;
  race_results: number;
  qualifying_results: number;
  driver_features: number;
  constructor_features: number;
  training_examples: number;
  backtest_predictions: number;
};

export type F1RaceWorkspace = {
  season: number;
  round: number;
  race?: F1RaceSummary | null;
  race_results: F1RaceResult[];
  qualifying_results: F1QualifyingResult[];
  session_links: F1SessionRaceLink[];
};

export function getF1Dashboard(season: number, round: number) {
  return getJson<F1DashboardPayload | null>(
    `/f1/dashboard/seasons/${season}/rounds/${round}?event_limit=80`,
    null,
    15000,
  );
}

export function getF1StoredRaces(season: number) {
  return getJson<F1RaceSummary[]>(`/f1/stored/seasons/${season}/races?limit=100`, [], 10000);
}

export function getF1RaceResults(season: number, round?: number) {
  const roundQuery = round ? `&round=${round}` : "";
  const limit = 1000;
  return getJson<F1RaceResult[]>(`/f1/stored/seasons/${season}/race-results?limit=${limit}${roundQuery}`, [], round ? 5000 : 15000);
}

export function getF1QualifyingResults(season: number, round?: number) {
  const roundQuery = round ? `&round=${round}` : "";
  const limit = 1000;
  return getJson<F1QualifyingResult[]>(`/f1/stored/seasons/${season}/qualifying-results?limit=${limit}${roundQuery}`, [], round ? 5000 : 15000);
}

export function getF1SessionRaceLinks(season: number, round?: number) {
  const roundQuery = round ? `&round=${round}` : "";
  const limit = 1000;
  return getJson<F1SessionRaceLink[]>(`/f1/sessions/seasons/${season}/race-links?limit=${limit}${roundQuery}`, [], round ? 5000 : 10000);
}

export function getF1RaceWorkspace(season: number, round: number) {
  return getJson<F1RaceWorkspace | null>(`/f1/stored/seasons/${season}/rounds/${round}/workspace`, null, 10000);
}

export function getF1ModelVersions() {
  return getJson<F1ModelVersion[]>("/f1/models/versions?limit=20", [], 10000);
}

export function getF1BacktestPredictions(season: number) {
  return getJson<F1BacktestPrediction[]>(`/f1/models/seasons/${season}/backtest?limit=1000`, [], 10000);
}

export function getF1Sources() {
  return getJson<F1DataSource[]>("/f1/sources", [], 10000);
}

export function getF1LiveReadiness() {
  return getJson<F1LiveReadiness | null>("/f1/live-readiness", null, 10000);
}

export function getF1DataCoverage() {
  return getJson<F1DataCoverage[]>("/f1/data/coverage", [], 10000);
}
