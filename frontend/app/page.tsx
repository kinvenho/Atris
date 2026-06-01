import AppShell from "@/components/AppShell";
import RecommendationCard from "@/components/RecommendationCard";
import { getAgentRuns, getPerformance, getRecommendations } from "@/lib/api";

export default async function Home() {
  const [recommendations, performance, runs] = await Promise.all([
    getRecommendations(),
    getPerformance(),
    getAgentRuns(),
  ]);
  const latestRun = runs[0];

  return (
    <AppShell>
      <main className="container">
        <section className="hero">
          <div>
            <div className="eyebrow">
              <span className="status-dot" />
              Live market scanner
            </div>
            <h1 className="hero-title">
              Mispriced <span>Polymarket</span> signals
            </h1>
            <p className="hero-copy">
              Atris scans prediction markets, gathers current context, estimates fair probability,
              and publishes only when the edge clears confidence thresholds.
            </p>
          </div>
          <div className="panel">
            <div className="metric-label">Latest Agent Run</div>
            <div className="metric-value accent">{latestRun?.status ?? "waiting"}</div>
            <div className="detail-list">
              <div className="detail-row">
                <span className="metric-label">Scanned</span>
                <strong className="mono">{latestRun?.markets_scanned ?? 0}</strong>
              </div>
              <div className="detail-row">
                <span className="metric-label">Evaluated</span>
                <strong className="mono">{latestRun?.candidates_evaluated ?? 0}</strong>
              </div>
              <div className="detail-row">
                <span className="metric-label">Published</span>
                <strong className="mono">{latestRun?.recommendations_published ?? 0}</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="metric-grid">
          <div className="metric-card">
            <div className="metric-label">Active Signals</div>
            <div className="metric-value">{recommendations.length}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Total Predictions</div>
            <div className="metric-value">{performance.total_predictions}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Accuracy</div>
            <div className="metric-value accent">{Math.round(performance.accuracy_rate * 100)}%</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Pending</div>
            <div className="metric-value violet-text">{performance.pending}</div>
          </div>
        </section>

        <section>
          <div className="toolbar">
            <input className="searchbox" placeholder="Search markets, outcomes, signals..." readOnly />
            <div className="eyebrow">
              <span className="status-dot" />
              {recommendations.length} signals found
            </div>
          </div>

          {recommendations.length ? (
            <div className="feed-grid">
              {recommendations.map((recommendation) => (
                <RecommendationCard key={recommendation.id} recommendation={recommendation} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              No active recommendations yet. The backend is scanning successfully; current markets have not cleared
              the configured edge and confidence thresholds.
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
