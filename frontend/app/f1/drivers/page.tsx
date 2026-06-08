import AppShell from "@/components/AppShell";
import { F1RaceResult, formatDate, formatPercent, getF1DataCoverage, getF1RaceResults } from "@/lib/api";
import { driverName } from "@/lib/f1Format";
import Link from "next/link";

type DriverStanding = {
  id: string;
  code: string;
  team: string;
  points: number;
  starts: number;
  wins: number;
  podiums: number;
  bestFinish: number | null;
  latestRound: number;
  latestRace?: string | null;
};

type F1DriversPageProps = {
  searchParams: Promise<{
    season?: string;
  }>;
};

function resultPosition(result: F1RaceResult) {
  return result.position_order ?? result.position ?? null;
}

function buildDriverStandings(results: F1RaceResult[]) {
  const standings = new Map<string, DriverStanding>();

  for (const result of results) {
    const position = resultPosition(result);
    const row = standings.get(result.driver_id) ?? {
      id: result.driver_id,
      code: result.driver_code ?? result.driver_id,
      team: result.constructor_name ?? "-",
      points: 0,
      starts: 0,
      wins: 0,
      podiums: 0,
      bestFinish: null,
      latestRound: 0,
      latestRace: null,
    };

    row.points += Number(result.points ?? 0);
    row.starts += 1;
    if (position === 1) row.wins += 1;
    if (position !== null && position <= 3) row.podiums += 1;
    if (position !== null) row.bestFinish = row.bestFinish === null ? position : Math.min(row.bestFinish, position);
    if (Number(result.round) >= row.latestRound) {
      row.latestRound = Number(result.round);
      row.latestRace = result.race_name;
      row.team = result.constructor_name ?? row.team;
    }
    standings.set(result.driver_id, row);
  }

  return [...standings.values()].sort((a, b) => b.points - a.points || b.wins - a.wins || b.podiums - a.podiums);
}

export default async function F1DriversPage({ searchParams }: F1DriversPageProps) {
  const [{ season: seasonParam }, coverage] = await Promise.all([searchParams, getF1DataCoverage()]);
  const seasons = coverage.map((row) => row.season);
  const selectedSeason = Number(seasonParam || seasons[0] || 2024);
  const season = seasons.includes(selectedSeason) ? selectedSeason : seasons[0] ?? selectedSeason;
  const results = await getF1RaceResults(season);
  const standings = buildDriverStandings(results);
  const leader = standings[0];
  const pointsTotal = standings.reduce((total, row) => total + row.points, 0);

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Driver Index</span>
            <span>{season}</span>
            <span>{standings.length || "No"} drivers</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">Driver Intelligence</h1>
              <p className="f1-subtitle">Season standings built from stored race results, points, wins, podiums, and starts.</p>
            </div>
            <div className="f1-race-clock">
              <span>Leader</span>
              <strong>{leader?.code ?? "Pending"}</strong>
              <small>{leader?.latestRace ?? "No classified results"}</small>
            </div>
          </div>
        </section>

        <nav className="f1-season-switcher" aria-label="Season selector">
          {seasons.map((seasonOption) => (
            <a key={seasonOption} href={`/f1/drivers?season=${seasonOption}`} className={seasonOption === season ? "active" : ""}>
              {seasonOption}
            </a>
          ))}
        </nav>

        <section className="f1-data-strip">
          <div className="f1-data-tile">
            <span>Drivers</span>
            <strong>{standings.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Points Issued</span>
            <strong>{pointsTotal.toFixed(0)}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Race Rows</span>
            <strong>{results.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Latest Row</span>
            <strong>{formatDate(results.at(-1)?.race_time ?? null)}</strong>
          </div>
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Driver Board</span>
              <h2>Season Classification</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              stored_results
            </div>
          </div>
          {standings.length ? (
            <div className="f1-table-wrap">
              <table className="f1-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Driver</th>
                    <th>Team</th>
                    <th>Points</th>
                    <th>Wins</th>
                    <th>Podiums</th>
                    <th>Starts</th>
                    <th>Best</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map((driver, index) => (
                    <tr key={driver.id}>
                      <td className="f1-rank">{index + 1}</td>
                      <td>
                        <Link href={`/f1/drivers/${driver.id}?season=${season}`} className="f1-command-link">
                          {driver.code}
                        </Link>
                      </td>
                      <td>{driver.team}</td>
                      <td>{driver.points}</td>
                      <td>{driver.wins}</td>
                      <td>{driver.podiums}</td>
                      <td>{driver.starts}</td>
                      <td>{driver.bestFinish ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="f1-empty-panel">
              <span>Driver Layer Empty</span>
              <strong>No stored race results are available from the API for {season} yet.</strong>
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
