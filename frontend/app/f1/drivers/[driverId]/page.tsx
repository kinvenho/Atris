import AppShell from "@/components/AppShell";
import { F1RaceResult, formatDate, getF1DataCoverage, getF1RaceResults } from "@/lib/api";
import { driverName } from "@/lib/f1Format";
import Link from "next/link";

type F1DriverDetailPageProps = {
  params: Promise<{
    driverId: string;
  }>;
  searchParams: Promise<{
    season?: string;
  }>;
};

function resultPosition(result: F1RaceResult) {
  return result.position_order ?? result.position ?? null;
}

export default async function F1DriverDetailPage({ params, searchParams }: F1DriverDetailPageProps) {
  const [{ driverId }, { season: seasonParam }, coverage] = await Promise.all([params, searchParams, getF1DataCoverage()]);
  const seasons = coverage.map((row) => row.season);
  const selectedSeason = Number(seasonParam || seasons[0] || 2024);
  const season = seasons.includes(selectedSeason) ? selectedSeason : seasons[0] ?? selectedSeason;
  const results = (await getF1RaceResults(season))
    .filter((result) => result.driver_id === driverId)
    .sort((a, b) => Number(a.round) - Number(b.round));
  const latest = results.at(-1);
  const points = results.reduce((sum, result) => sum + Number(result.points ?? 0), 0);
  const wins = results.filter((result) => resultPosition(result) === 1).length;
  const podiums = results.filter((result) => {
    const position = resultPosition(result);
    return position !== null && position <= 3;
  }).length;
  const bestFinish = results.reduce<number | null>((best, result) => {
    const position = resultPosition(result);
    if (position === null) return best;
    return best === null ? position : Math.min(best, position);
  }, null);

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Driver File</span>
            <span>{season}</span>
            <span>{latest?.constructor_name ?? "Unknown team"}</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">{latest?.driver_code ?? driverName(driverId)}</h1>
              <nav className="f1-breadcrumb" aria-label="Driver breadcrumbs">
                <Link href="/">Command</Link>
                <Link href={`/f1/drivers?season=${season}`}>Drivers</Link>
                <span>{driverId}</span>
              </nav>
            </div>
            <div className="f1-race-clock">
              <span>Latest Result</span>
              <strong>{latest?.race_name ?? "Pending"}</strong>
              <small>{latest ? `R${latest.round} / P${resultPosition(latest) ?? "-"}` : "No classified rows"}</small>
            </div>
          </div>
        </section>

        <section className="f1-data-strip">
          <div className="f1-data-tile">
            <span>Points</span>
            <strong>{points}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Wins</span>
            <strong>{wins}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Podiums</span>
            <strong>{podiums}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Best Finish</span>
            <strong>{bestFinish ?? "Pending"}</strong>
          </div>
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Driver Results</span>
              <h2>Season Race Log</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              stored_results
            </div>
          </div>
          {results.length ? (
            <div className="f1-table-wrap">
              <table className="f1-table">
                <thead>
                  <tr>
                    <th>Round</th>
                    <th>Race</th>
                    <th>Team</th>
                    <th>Grid</th>
                    <th>Finish</th>
                    <th>Points</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result) => (
                    <tr key={`${result.round}-${result.driver_id}`}>
                      <td className="f1-rank">R{result.round}</td>
                      <td>{result.race_name ?? "-"}</td>
                      <td>{result.constructor_name ?? "-"}</td>
                      <td>{result.grid ?? "-"}</td>
                      <td>{result.position_text ?? resultPosition(result) ?? "-"}</td>
                      <td>{result.points ?? 0}</td>
                      <td>{result.status ?? result.race_time ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="f1-empty-panel">
              <span>Driver Layer Empty</span>
              <strong>No stored race results are available for this driver in {season} yet.</strong>
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
