import AppShell from "@/components/AppShell";
import AnimatedNumber from "@/components/AnimatedNumber";
import RecommendationCard from "@/components/RecommendationCard";
import SignalSearch from "@/components/SignalSearch";
import { formatDate, getAgentRuns, getRecommendations } from "@/lib/api";

export default async function Home() {
  const [recommendations, runs] = await Promise.all([
    getRecommendations(),
    getAgentRuns(),
  ]);
  const latestRun = runs[0];
  const runTotals = runs.reduce(
    (totals, run) => ({
      scanned: totals.scanned + run.markets_scanned,
      evaluated: totals.evaluated + run.candidates_evaluated,
      published: totals.published + run.recommendations_published,
    }),
    { scanned: 0, evaluated: 0, published: 0 },
  );

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
            <div
              className={
                latestRun?.status === "failed"
                  ? "metric-value red-text"
                  : latestRun?.status === "partial"
                    ? "metric-value violet-text"
                    : "metric-value accent"
              }
            >
              {latestRun?.status ?? "waiting"}
            </div>
            <div className="detail-list">
              <div className="detail-row">
                <span className="metric-label">Scanned</span>
                <strong className="mono">
                  <AnimatedNumber value={latestRun?.markets_scanned ?? 0} />
                </strong>
              </div>
              <div className="detail-row">
                <span className="metric-label">Evaluated</span>
                <strong className="mono">
                  <AnimatedNumber value={latestRun?.candidates_evaluated ?? 0} />
                </strong>
              </div>
              <div className="detail-row">
                <span className="metric-label">Published</span>
                <strong className="mono">
                  <AnimatedNumber value={latestRun?.recommendations_published ?? 0} />
                </strong>
              </div>
            </div>
          </div>
        </section>

        <section className="metric-grid">
          <div className="metric-card">
            <div className="metric-label">Active Signals</div>
            <AnimatedNumber className="metric-value" value={recommendations.length} />
          </div>
          <div className="metric-card">
            <div className="metric-label">Markets Scanned</div>
            <AnimatedNumber className="metric-value" value={runTotals.scanned} />
          </div>
          <div className="metric-card">
            <div className="metric-label">Candidates Evaluated</div>
            <AnimatedNumber className="metric-value accent" value={runTotals.evaluated} />
          </div>
          <div className="metric-card">
            <div className="metric-label">Published</div>
            <AnimatedNumber className="metric-value violet-text" value={runTotals.published} />
          </div>
        </section>

        <section>
          <div className="toolbar">
            <SignalSearch recommendations={recommendations} />
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
              No active recommendations yet. Atris will publish here once a run clears the configured edge and
              confidence thresholds.
            </div>
          )}
        </section>

        <section className="mt-10">
          <div className="section-title">
            <span className="status-dot" />
            Recent Agent Runs
          </div>
          <div className="table-panel mt-5">
            <table className="rank-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Status</th>
                  <th>Scanned</th>
                  <th>Evaluated</th>
                  <th>Published</th>
                  <th>Completed</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 5).map((run, index) => (
                  <tr key={run.id}>
                    <td>
                      <span className="rank-cell">#{index + 1}</span>
                    </td>
                    <td className={run.status === "success" ? "lime-text" : run.status === "failed" ? "red-text" : "violet-text"}>
                      {run.status}
                    </td>
                    <td>{run.markets_scanned}</td>
                    <td>{run.candidates_evaluated}</td>
                    <td>{run.recommendations_published}</td>
                    <td>{formatDate(run.completed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </AppShell>
  );
}
