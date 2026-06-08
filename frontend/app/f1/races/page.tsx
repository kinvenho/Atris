import Link from "next/link";
import AppShell from "@/components/AppShell";
import { F1RaceSummary, formatDate, getF1DataCoverage, getF1StoredRaces } from "@/lib/api";

function raceRound(race: F1RaceSummary) {
  return Number(race.round ?? 0);
}

type F1RacesPageProps = {
  searchParams: Promise<{
    season?: string;
  }>;
};

export default async function F1RacesPage({ searchParams }: F1RacesPageProps) {
  const [{ season: seasonParam }, coverage] = await Promise.all([searchParams, getF1DataCoverage()]);
  const seasons = coverage.map((row) => row.season);
  const selectedSeason = Number(seasonParam || seasons[0] || 2024);
  const season = seasons.includes(selectedSeason) ? selectedSeason : seasons[0] ?? selectedSeason;
  const storedRaces = await getF1StoredRaces(season);
  const sortedRaces = [...storedRaces]
    .filter((race) => Number(race.season ?? season) === season)
    .sort((a, b) => raceRound(a) - raceRound(b));

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Race Index</span>
            <span>{season}</span>
            <span>{sortedRaces.length} rounds</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">Race Command Index</h1>
              <p className="f1-subtitle">Select a race to inspect predictions, sessions, race control, and model freshness.</p>
            </div>
          </div>
        </section>

        <nav className="f1-season-switcher" aria-label="Season selector">
          {seasons.map((seasonOption) => (
            <a
              key={seasonOption}
              href={`/f1/races?season=${seasonOption}`}
              className={seasonOption === season ? "active" : ""}
            >
              {seasonOption}
            </a>
          ))}
        </nav>

        <section className="f1-main-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Season Schedule</span>
              <h2>Stored Race Layer</h2>
            </div>
            <div className="f1-status">
              <span className="f1-live-dot" />
              Command URLs
            </div>
          </div>
          {sortedRaces.length ? (
          <div className="f1-table-wrap">
            <table className="f1-table f1-race-command-table">
              <thead>
                <tr>
                  <th>Rnd.</th>
                  <th>Grand Prix</th>
                  <th>Circuit</th>
                  <th>Location</th>
                  <th>Date</th>
                  <th>Command</th>
                </tr>
              </thead>
              <tbody>
                {sortedRaces.map((race) => {
                  const round = raceRound(race);
                  return (
                    <tr key={`${race.season ?? season}-${round}`}>
                      <td className="f1-race-round">R{round}</td>
                      <td>
                        <strong>{race.race_name ?? "Grand Prix"}</strong>
                      </td>
                      <td>{race.circuit_name ?? "Circuit"}</td>
                      <td>{race.locality ?? "-"} / {race.country ?? "-"}</td>
                      <td>{formatDate(race.race_date)}</td>
                      <td>
                        <Link href={`/f1/races/${race.season ?? season}/${round}`} className="f1-command-link">
                          Open
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          ) : (
            <div className="f1-empty-panel">
              <span>Race Layer Empty</span>
              <strong>No stored races are available from the API for {season} yet.</strong>
            </div>
          )}
        </section>
      </main>
    </AppShell>
  );
}
