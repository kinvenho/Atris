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

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(8000),
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
