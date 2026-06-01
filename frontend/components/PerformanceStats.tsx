import { AgentRun, formatDate, formatPercent, formatSignedPercent, PerformanceSnapshot } from "@/lib/api";

export default function PerformanceStats({
  performance,
  runs,
}: {
  performance: PerformanceSnapshot;
  runs: AgentRun[];
}) {
  return (
    <div className="grid gap-8">
      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-label">Total Predictions</div>
          <div className="metric-value">{performance.total_predictions}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Accuracy Rate</div>
          <div className="metric-value accent">{formatPercent(performance.accuracy_rate, 0)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Pending</div>
          <div className="metric-value">{performance.pending}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Average Edge</div>
          <div className="metric-value violet-text">{formatSignedPercent(performance.average_edge)}</div>
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
