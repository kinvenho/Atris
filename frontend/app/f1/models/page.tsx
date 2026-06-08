import AppShell from "@/components/AppShell";
import {
  F1BacktestPrediction,
  F1ModelVersion,
  formatDate,
  formatPercent,
  getF1BacktestPredictions,
  getF1DataCoverage,
  getF1ModelVersions,
} from "@/lib/api";

function metric(model: F1ModelVersion, key: string) {
  return Number(model.metrics?.eval?.[key] ?? model.metrics?.train?.[key] ?? 0);
}

function accuracy(rows: F1BacktestPrediction[]) {
  const scoredRows = rows.filter((row) => typeof row.label === "boolean" && typeof row.predicted_label === "boolean");
  if (!scoredRows.length) return 0;
  return scoredRows.filter((row) => row.label === row.predicted_label).length / scoredRows.length;
}

type F1ModelsPageProps = {
  searchParams: Promise<{
    season?: string;
  }>;
};

export default async function F1ModelsPage({ searchParams }: F1ModelsPageProps) {
  const [{ season: seasonParam }, coverage, models] = await Promise.all([
    searchParams,
    getF1DataCoverage(),
    getF1ModelVersions(),
  ]);
  const seasons = coverage.map((row) => row.season);
  const selectedSeason = Number(seasonParam || seasons[0] || 2024);
  const season = seasons.includes(selectedSeason) ? selectedSeason : seasons[0] ?? selectedSeason;
  const backtests = await getF1BacktestPredictions(season);
  const activeModels = models.filter((model) => model.status === "active");
  const recentBacktests = backtests.slice(0, 12);
  const backtestAccuracy = accuracy(backtests);

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Model Index</span>
            <span>{season}</span>
            <span>{models.length || "No"} versions</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">Model Intelligence</h1>
              <p className="f1-subtitle">Training status, evaluation metrics, and backtest audit surface.</p>
            </div>
          </div>
        </section>

        <nav className="f1-season-switcher" aria-label="Season selector">
          {seasons.map((seasonOption) => (
            <a key={seasonOption} href={`/f1/models?season=${seasonOption}`} className={seasonOption === season ? "active" : ""}>
              {seasonOption}
            </a>
          ))}
        </nav>

        <section className="f1-data-strip">
          <div className="f1-data-tile">
            <span>Versions</span>
            <strong>{models.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Active</span>
            <strong>{activeModels.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Backtests</span>
            <strong>{backtests.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Accuracy</span>
            <strong>{formatPercent(backtestAccuracy, 0)}</strong>
          </div>
        </section>

        <section className="f1-model-grid">
          {(models.length ? models : []).map((model) => (
            <article key={model.id} className="f1-main-panel f1-model-card">
              <div className="f1-panel-header">
                <div>
                  <span className="f1-kicker">{model.outcome_type}</span>
                  <h2>{model.model_name}</h2>
                </div>
                <div className="f1-status">
                  <span className="f1-live-dot" />
                  {model.status}
                </div>
              </div>
              <div className="f1-model-card-body">
                <div>
                  <span>Version</span>
                  <strong>{model.version}</strong>
                </div>
                <div>
                  <span>Brier</span>
                  <strong>{metric(model, "brier").toFixed(3)}</strong>
                </div>
                <div>
                  <span>Log Loss</span>
                  <strong>{metric(model, "log_loss").toFixed(3)}</strong>
                </div>
                <div>
                  <span>Accuracy</span>
                  <strong>{formatPercent(metric(model, "accuracy"), 0)}</strong>
                </div>
                <div className="wide">
                  <span>Trained</span>
                  <strong>{formatDate(model.metrics?.trained_at ?? model.created_at)}</strong>
                </div>
              </div>
            </article>
          ))}
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Backtest</span>
              <h2>Recent Prediction Audit</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              eval split
            </div>
          </div>
          {recentBacktests.length ? (
            <div className="f1-table-wrap">
              <table className="f1-table">
                <thead>
                  <tr>
                    <th>Round</th>
                    <th>Race</th>
                    <th>Driver</th>
                    <th>Outcome</th>
                    <th>Probability</th>
                    <th>Label</th>
                    <th>Pred.</th>
                  </tr>
                </thead>
                <tbody>
                  {recentBacktests.map((row, index) => (
                    <tr key={`${row.round}-${row.driver_id}-${row.outcome_type}-${index}`}>
                      <td className="f1-rank">{row.round}</td>
                      <td>{row.race_name ?? "-"}</td>
                      <td>
                        <strong>{row.driver_code ?? row.driver_id}</strong>
                      </td>
                      <td>{row.outcome_type}</td>
                      <td>{formatPercent(row.probability, 0)}</td>
                      <td>{typeof row.label === "boolean" ? String(row.label) : "-"}</td>
                      <td>{typeof row.predicted_label === "boolean" ? String(row.predicted_label) : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="f1-empty-panel">
              <span>Backtest Pending</span>
              <strong>No stored model backtest rows are available yet.</strong>
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
