import AppShell from "@/components/AppShell";
import { F1RaceResult, getF1DataCoverage, getF1RaceResults } from "@/lib/api";
import Link from "next/link";

type ConstructorStanding = {
  id: string;
  name: string;
  drivers: Set<string>;
  points: number;
  wins: number;
  podiums: number;
  starts: number;
  bestFinish: number | null;
};

type F1ConstructorsPageProps = {
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

function buildConstructorStandings(results: F1RaceResult[]) {
  const standings = new Map<string, ConstructorStanding>();

  for (const result of results) {
    const id = constructorId(result.constructor_name);
    const position = resultPosition(result);
    const row = standings.get(id) ?? {
      id,
      name: result.constructor_name ?? "Unknown",
      drivers: new Set<string>(),
      points: 0,
      wins: 0,
      podiums: 0,
      starts: 0,
      bestFinish: null,
    };

    row.drivers.add(result.driver_code ?? result.driver_id);
    row.points += Number(result.points ?? 0);
    row.starts += 1;
    if (position === 1) row.wins += 1;
    if (position !== null && position <= 3) row.podiums += 1;
    if (position !== null) row.bestFinish = row.bestFinish === null ? position : Math.min(row.bestFinish, position);
    standings.set(id, row);
  }

  return [...standings.values()].sort((a, b) => b.points - a.points || b.wins - a.wins || b.podiums - a.podiums);
}

export default async function F1ConstructorsPage({ searchParams }: F1ConstructorsPageProps) {
  const [{ season: seasonParam }, coverage] = await Promise.all([searchParams, getF1DataCoverage()]);
  const seasons = coverage.map((row) => row.season);
  const selectedSeason = Number(seasonParam || seasons[0] || 2024);
  const season = seasons.includes(selectedSeason) ? selectedSeason : seasons[0] ?? selectedSeason;
  const results = await getF1RaceResults(season);
  const constructors = buildConstructorStandings(results);
  const topTeam = constructors[0];

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Team Index</span>
            <span>{season}</span>
            <span>{constructors.length || "No"} teams</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">Constructor Intelligence</h1>
              <p className="f1-subtitle">Season team classification built from stored race results, points, wins, podiums, and starts.</p>
            </div>
            <div className="f1-race-clock">
              <span>Top Team</span>
              <strong>{topTeam?.name ?? "Pending"}</strong>
              <small>{topTeam ? `${topTeam.points} pts` : "No classified results"}</small>
            </div>
          </div>
        </section>

        <nav className="f1-season-switcher" aria-label="Season selector">
          {seasons.map((seasonOption) => (
            <a key={seasonOption} href={`/f1/constructors?season=${seasonOption}`} className={seasonOption === season ? "active" : ""}>
              {seasonOption}
            </a>
          ))}
        </nav>

        <section className="f1-data-strip">
          <div className="f1-data-tile">
            <span>Teams</span>
            <strong>{constructors.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Race Rows</span>
            <strong>{results.length}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Total Wins</span>
            <strong>{constructors.reduce((sum, row) => sum + row.wins, 0)}</strong>
          </div>
          <div className="f1-data-tile">
            <span>Total Podiums</span>
            <strong>{constructors.reduce((sum, row) => sum + row.podiums, 0)}</strong>
          </div>
        </section>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Constructor Board</span>
              <h2>Team Classification</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              stored_results
            </div>
          </div>
          {constructors.length ? (
            <div className="f1-table-wrap">
              <table className="f1-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th>Drivers</th>
                    <th>Points</th>
                    <th>Wins</th>
                    <th>Podiums</th>
                    <th>Starts</th>
                    <th>Best</th>
                  </tr>
                </thead>
                <tbody>
                  {constructors.map((constructor, index) => (
                    <tr key={constructor.id}>
                      <td className="f1-rank">{index + 1}</td>
                      <td>
                        <Link className="f1-command-link wide" href={`/f1/constructors/${constructor.id}?season=${season}`}>
                          {constructor.name}
                        </Link>
                      </td>
                      <td>{[...constructor.drivers].join(" / ")}</td>
                      <td>{constructor.points}</td>
                      <td>{constructor.wins}</td>
                      <td>{constructor.podiums}</td>
                      <td>{constructor.starts}</td>
                      <td>{constructor.bestFinish ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="f1-empty-panel">
              <span>Constructor Layer Empty</span>
              <strong>No stored race results are available from the API for {season} yet.</strong>
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
