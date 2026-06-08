import AppShell from "@/components/AppShell";
import { getF1DataCoverage, getF1LiveReadiness, getF1Sources } from "@/lib/api";

function statusLabel(status: string) {
  return status.replace("_", " ");
}

export default async function F1DataPage() {
  const [sources, readiness, coverage] = await Promise.all([
    getF1Sources(),
    getF1LiveReadiness(),
    getF1DataCoverage(),
  ]);
  const readySources = sources.filter((source) => source.status === "ready").length;
  const liveSources = sources.filter((source) => source.kind === "live");
  const latestCoverage = coverage[0];
  const historicalSeasons = coverage.filter((row) => row.races > 0).length;
  const trainingRows = coverage.reduce((sum, row) => sum + row.training_examples, 0);

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Data Layer</span>
            <span>{sources.length || "No"} sources</span>
            <span>{readySources} ready</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">Data Readiness</h1>
              <p className="f1-subtitle">Provider coverage, live strategy, storage policy, and roadmap status.</p>
            </div>
          </div>
        </section>

        <section className="f1-data-strip">
          <div className="f1-data-tile">
            <span>Historical Seasons</span>
            <strong>{historicalSeasons || "Pending"}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Latest Season</span>
            <strong>{latestCoverage?.season ?? "Pending"}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Training Rows</span>
            <strong>{trainingRows}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Ready Sources</span>
            <strong>{readySources}</strong>
          </div>
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Warehouse Coverage</span>
              <h2>Historical Data Stack</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              compact rows
            </div>
          </div>
          {coverage.length ? (
            <div className="f1-table-wrap">
              <table className="f1-table f1-coverage-table">
                <thead>
                  <tr>
                    <th>Season</th>
                    <th>Races</th>
                    <th>Results</th>
                    <th>Qualifying</th>
                    <th>Drivers</th>
                    <th>Teams</th>
                    <th>Training</th>
                    <th>Backtests</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.map((row) => (
                    <tr key={row.season}>
                      <td className="f1-rank">{row.season}</td>
                      <td>{row.races}</td>
                      <td>{row.race_results}</td>
                      <td>{row.qualifying_results}</td>
                      <td>{row.driver_features}</td>
                      <td>{row.constructor_features}</td>
                      <td>{row.training_examples}</td>
                      <td>{row.backtest_predictions}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="f1-empty-panel">
              <span>Coverage Pending</span>
              <strong>No stored historical coverage rows are available yet.</strong>
            </div>
          )}
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Readiness Policy</span>
              <h2>Live Data Strategy</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              governed
            </div>
          </div>
          <div className="f1-policy-grid">
            <div>
              <span>Preferred Path</span>
              <strong>{readiness?.preferred_live_path ?? "Pending live readiness response."}</strong>
            </div>
            <div>
              <span>Supabase Policy</span>
              <strong>{readiness?.supabase_storage_policy ?? "Pending storage policy response."}</strong>
            </div>
          </div>
        </section>

        <section className="f1-source-grid">
          {sources.map((source) => (
            <article key={source.name} className="f1-main-panel f1-source-card">
              <div className="f1-panel-header">
                <div>
                  <span className="f1-kicker">{source.kind}</span>
                  <h2>{source.name}</h2>
                </div>
                <div className="f1-status">
                  <span className="f1-live-dot" />
                  {statusLabel(source.status)}
                </div>
              </div>
              <div className="f1-source-card-body">
                <div>
                  <span>Access</span>
                  <strong>{source.access}</strong>
                </div>
                <div>
                  <span>Role</span>
                  <strong>{source.role}</strong>
                </div>
                <div>
                  <span>Notes</span>
                  <strong>{source.notes}</strong>
                </div>
                <a href={source.url} target="_blank" rel="noreferrer">
                  Source
                </a>
              </div>
            </article>
          ))}
        </section>
      </main>
    </AppShell>
  );
}
