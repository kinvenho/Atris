import AnimatedNumber from "@/components/AnimatedNumber";
import { AgentRun, formatDate, PerformanceSnapshot } from "@/lib/api";

export default function PerformanceStats({
  performance,
  runs,
}: {
  performance: PerformanceSnapshot;
  runs: AgentRun[];
}) {
  const runTotals = runs.reduce(
    (totals, run) => ({
      scanned: totals.scanned + run.markets_scanned,
      evaluated: totals.evaluated + run.candidates_evaluated,
      published: totals.published + run.recommendations_published,
      failed: totals.failed + (run.status === "failed" ? 1 : 0),
    }),
    { scanned: 0, evaluated: 0, published: 0, failed: 0 },
  );
  const successRate = runs.length ? ((runs.length - runTotals.failed) / runs.length) * 100 : 0;

  return (
    <div className="grid gap-8">
      <div className="metric-grid">
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
        <div className="metric-card">
          <div className="metric-label">Run Success</div>
          <AnimatedNumber className="metric-value" value={successRate} suffix="%" />
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">Total Predictions</div>
          <AnimatedNumber className="metric-value" value={performance.total_predictions} />
        </div>
        <div className="metric-card">
          <div className="metric-label">Accuracy Rate</div>
          <AnimatedNumber className="metric-value accent" value={performance.accuracy_rate * 100} suffix="%" />
        </div>
        <div className="metric-card">
          <div className="metric-label">Pending</div>
          <AnimatedNumber className="metric-value" value={performance.pending} />
        </div>
        <div className="metric-card">
          <div className="metric-label">Average Edge</div>
          <AnimatedNumber
            className="metric-value violet-text"
            decimals={1}
            signed
            suffix="%"
            value={performance.average_edge * 100}
          />
        </div>
      </div>

      <section className="table-panel">
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
            {runs.slice(0, 8).map((run, index) => (
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
      </section>
    </div>
  );
}
