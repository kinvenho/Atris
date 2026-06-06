import Link from "next/link";
import AppShell from "@/components/AppShell";
import { F1RaceSummary, formatDate, getF1StoredRaces } from "@/lib/api";

const FALLBACK_RACES: F1RaceSummary[] = [
  { season: 2024, round: 1, race_name: "Bahrain Grand Prix", circuit_name: "Bahrain International Circuit", locality: "Sakhir", country: "Bahrain", race_date: "2024-03-02" },
  { season: 2024, round: 2, race_name: "Saudi Arabian Grand Prix", circuit_name: "Jeddah Corniche Circuit", locality: "Jeddah", country: "Saudi Arabia", race_date: "2024-03-09" },
  { season: 2024, round: 3, race_name: "Australian Grand Prix", circuit_name: "Albert Park Grand Prix Circuit", locality: "Melbourne", country: "Australia", race_date: "2024-03-24" },
  { season: 2024, round: 4, race_name: "Japanese Grand Prix", circuit_name: "Suzuka Circuit", locality: "Suzuka", country: "Japan", race_date: "2024-04-07" },
  { season: 2024, round: 5, race_name: "Chinese Grand Prix", circuit_name: "Shanghai International Circuit", locality: "Shanghai", country: "China", race_date: "2024-04-21" },
  { season: 2024, round: 6, race_name: "Miami Grand Prix", circuit_name: "Miami International Autodrome", locality: "Miami", country: "United States", race_date: "2024-05-05" },
];

function raceRound(race: F1RaceSummary) {
  return Number(race.round ?? 0);
}

export default async function F1RacesPage() {
  const storedRaces = await getF1StoredRaces(2024);
  const races = storedRaces.length ? storedRaces : FALLBACK_RACES;
  const sortedRaces = [...races].sort((a, b) => raceRound(a) - raceRound(b));

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-compact-hero">
          <div className="f1-context">
            <span className="f1-pill">Race Index</span>
            <span>2024</span>
            <span>{sortedRaces.length} rounds</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title compact">Race Command Index</h1>
              <p className="f1-subtitle">Select a race to inspect predictions, sessions, race control, and model freshness.</p>
            </div>
          </div>
        </section>

        <section className="f1-panel">
          <div className="f1-panel-header">
            <div>
              <span className="f1-kicker">Season Schedule</span>
              <h2>Stored Race Layer</h2>
            </div>
            <span className="f1-count">Command URLs</span>
          </div>
          <div className="f1-race-list">
            {sortedRaces.map((race) => {
              const round = raceRound(race);
              return (
                <Link key={`${race.season ?? 2024}-${round}`} href={`/f1/races/${race.season ?? 2024}/${round}`} className="f1-race-row">
                  <span className="f1-race-round">R{round}</span>
                  <strong>{race.race_name ?? "Grand Prix"}</strong>
                  <span>{race.circuit_name ?? "Circuit"}</span>
                  <span>{race.locality ?? "-"} / {race.country ?? "-"}</span>
                  <span>{formatDate(race.race_date)}</span>
                </Link>
              );
            })}
          </div>
        </section>
      </main>
    </AppShell>
  );
}
