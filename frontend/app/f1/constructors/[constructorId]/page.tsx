import AppShell from "@/components/AppShell";
import { F1RaceResult, getF1DataCoverage, getF1RaceResults } from "@/lib/api";
import { driverName } from "@/lib/f1Format";
import Link from "next/link";

type F1ConstructorDetailPageProps = {
  params: Promise<{
    constructorId: string;
  }>;
  searchParams: Promise<{
    season?: string;
  }>;
};

function constructorId(name?: string | null) {
  return (name ?? "unknown").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function resultPosition(result: F1RaceResult) {
  return result.position_order ?? result.position ?? null;
}

export default async function F1ConstructorDetailPage({ params, searchParams }: F1ConstructorDetailPageProps) {
  const [{ constructorId: selectedConstructorId }, { season: seasonParam }, coverage] = await Promise.all([
    params,
    searchParams,
    getF1DataCoverage(),
  ]);
  const seasons = coverage.map((row) => row.season);
  const selectedSeason = Number(seasonParam || seasons[0] || 2024);
  const season = seasons.includes(selectedSeason) ? selectedSeason : seasons[0] ?? selectedSeason;
  const results = (await getF1RaceResults(season))
    .filter((result) => constructorId(result.constructor_name) === selectedConstructorId)
    .sort((a, b) => Number(a.round) - Number(b.round) || (resultPosition(a) ?? 99) - (resultPosition(b) ?? 99));
  const name = results[0]?.constructor_name ?? selectedConstructorId.replaceAll("_", " ");
  const points = results.reduce((sum, result) => sum + Number(result.points ?? 0), 0);
  const wins = results.filter((result) => resultPosition(result) === 1).length;
  const podiums = results.filter((result) => {
    const position = resultPosition(result);
    return position !== null && position <= 3;
  }).length;
  const drivers = [...new Set(results.map((result) => result.driver_code ?? driverName(result.driver_id)))];

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Team File</span>
            <span>{season}</span>
            <span>{drivers.length || "No"} drivers</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">{name}</h1>
              <nav className="f1-breadcrumb" aria-label="Team breadcrumbs">
                <Link href="/">Command</Link>
                <Link href={`/f1/constructors?season=${season}`}>Teams</Link>
                <span>{selectedConstructorId}</span>
              </nav>
            </div>
            <div className="f1-race-clock">
              <span>Season Points</span>
              <strong>{points}</strong>
              <small>{drivers.join(" / ") || "No classified rows"}</small>
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
            <span>Result Rows</span>
            <strong>{results.length}</strong>
          </div>
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Team Results</span>
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
                    <th>Driver</th>
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
                      <td>
                        <Link className="f1-command-link" href={`/f1/drivers/${result.driver_id}?season=${season}`}>
                          {result.driver_code ?? driverName(result.driver_id)}
                        </Link>
                      </td>
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
              <span>Constructor Layer Empty</span>
              <strong>No stored race results are available for this constructor in {season} yet.</strong>
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
