import AppShell from "@/components/AppShell";
import {
  F1DashboardPayload,
  F1Prediction,
  formatDate,
  formatPercent,
  getF1Dashboard,
} from "@/lib/api";

const TEAM_COLORS: Record<string, string> = {
  red_bull: "#3671c6",
  ferrari: "#e80020",
  mclaren: "#ff8000",
  mercedes: "#27f4d2",
  aston_martin: "#229971",
  alpine: "#0093cc",
  rb: "#6692ff",
  haas: "#b6babd",
  williams: "#64c4ff",
  kick_sauber: "#52e252",
};

const FALLBACK_DASHBOARD: F1DashboardPayload = {
  season: 2024,
  round: 4,
  race: {
    race_name: "Japanese Grand Prix",
    circuit_name: "Suzuka Circuit",
    locality: "Suzuka",
    country: "Japan",
    race_date: "2024-04-07",
    race_time: "05:00:00Z",
  },
  sessions: [
    { session_key: 9492, link: { session_name: "Practice 1", session_type: "Practice", date_start: "2024-04-05T02:30:00Z" } },
    { session_key: 9493, link: { session_name: "Practice 2", session_type: "Practice", date_start: "2024-04-05T06:00:00Z" } },
    { session_key: 9494, link: { session_name: "Practice 3", session_type: "Practice", date_start: "2024-04-06T02:30:00Z" } },
    { session_key: 9495, link: { session_name: "Qualifying", session_type: "Qualifying", date_start: "2024-04-06T06:00:00Z" } },
    {
      session_key: 9496,
      link: { session_name: "Race", session_type: "Race", date_start: "2024-04-07T05:00:00Z" },
      events: [
        { event_time: "2024-04-07T05:02:00Z", event_category: "race_control", message: "Track clear" },
        { event_time: "2024-04-07T05:08:00Z", event_category: "weather", message: "Dry running, light cloud" },
      ],
    },
  ],
  latest_race_weekend_predictions: {
    prediction_mode: "race_weekend",
    feature_set: "race_weekend_v1",
    generated_at: "2024-04-07T05:18:00Z",
    predictions: [
      { driver_id: "max_verstappen", driver_code: "VER", constructor_id: "red_bull", constructor_name: "Red Bull Racing", latest_position: 1, latest_lap_number: 12, points_finish_probability: 0.96, podium_finish_probability: 0.82, confidence: 0.78 },
      { driver_id: "perez", driver_code: "PER", constructor_id: "red_bull", constructor_name: "Red Bull Racing", latest_position: 2, latest_lap_number: 12, points_finish_probability: 0.9, podium_finish_probability: 0.64, confidence: 0.75 },
      { driver_id: "norris", driver_code: "NOR", constructor_id: "mclaren", constructor_name: "McLaren", latest_position: 3, latest_lap_number: 12, points_finish_probability: 0.84, podium_finish_probability: 0.41, confidence: 0.72 },
      { driver_id: "leclerc", driver_code: "LEC", constructor_id: "ferrari", constructor_name: "Ferrari", latest_position: 4, latest_lap_number: 12, points_finish_probability: 0.79, podium_finish_probability: 0.28, confidence: 0.71 },
      { driver_id: "hamilton", driver_code: "HAM", constructor_id: "mercedes", constructor_name: "Mercedes", latest_position: 7, latest_lap_number: 12, points_finish_probability: 0.57, podium_finish_probability: 0.11, confidence: 0.69 },
    ],
  },
  pre_race_predictions: null,
  freshness: {
    built_at: "2024-04-07T05:18:00Z",
    linked_sessions: 5,
    pre_race_prediction_count: 20,
    race_weekend_prediction_count: 20,
    latest_event_time: "2024-04-07T05:08:00Z",
    latest_prediction_built_at: "2024-04-07T05:18:00Z",
  },
};

function driverName(driverId: string) {
  return driverId
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function eventText(event: Record<string, unknown>) {
  return String(event.message ?? event.event ?? event.category ?? event.event_category ?? "Session update");
}

function probabilityDelta(current: F1Prediction, baseline?: F1Prediction) {
  if (!baseline) return null;
  return current.points_finish_probability - baseline.points_finish_probability;
}

export default async function F1Page() {
  const dashboard = (await getF1Dashboard(2024, 4)) ?? FALLBACK_DASHBOARD;
  const race = dashboard.race ?? FALLBACK_DASHBOARD.race;
  const liveBoard = dashboard.latest_race_weekend_predictions ?? dashboard.pre_race_predictions ?? FALLBACK_DASHBOARD.latest_race_weekend_predictions;
  const preRaceByDriver = new Map(
    (dashboard.pre_race_predictions?.predictions ?? []).map((prediction) => [prediction.driver_id, prediction]),
  );
  const predictions = [...(liveBoard?.predictions ?? [])].sort(
    (a, b) => Number(b.points_finish_probability || 0) - Number(a.points_finish_probability || 0),
  );
  const leader = predictions[0];
  const latestSession = [...dashboard.sessions].sort(
    (a, b) => String(b.link?.date_start ?? "").localeCompare(String(a.link?.date_start ?? "")),
  )[0];
  const events = dashboard.sessions.flatMap((session) => session.events ?? []).slice(0, 8);

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-hero">
          <div className="f1-context">
            <span className="f1-pill">F1 Command</span>
            <span>Round {dashboard.round}</span>
            <span>{dashboard.season}</span>
            <span>{race?.country ?? "Race weekend"}</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title">{race?.race_name ?? "Grand Prix"}</h1>
              <p className="f1-subtitle">
                {race?.circuit_name ?? "Circuit"} / {race?.locality ?? "Live race model"} /{" "}
                {liveBoard?.feature_set ?? "race_weekend_v1"}
              </p>
            </div>
            <div className="f1-race-clock">
              <span>Latest Build</span>
              <strong>{formatDate(dashboard.freshness?.built_at)}</strong>
              <small>{dashboard.freshness?.race_weekend_prediction_count ?? predictions.length} race-weekend predictions</small>
            </div>
          </div>
        </section>

        <section className="f1-command-grid">
          <div className="f1-main-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Prediction Board</span>
                <h2>Points Finish Control</h2>
              </div>
              <div className="f1-status">
                <span className="f1-live-dot" />
                {liveBoard?.prediction_mode ?? "pre_race"}
              </div>
            </div>

            <div className="f1-table-wrap">
              <table className="f1-table">
                <thead>
                  <tr>
                    <th>Pos.</th>
                    <th>Driver</th>
                    <th>Team</th>
                    <th>Points</th>
                    <th>Podium</th>
                    <th>Delta</th>
                    <th>Lap</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((prediction, index) => {
                    const delta = probabilityDelta(prediction, preRaceByDriver.get(prediction.driver_id));
                    const color = TEAM_COLORS[prediction.constructor_id ?? ""] ?? "#ff2d2d";
                    return (
                      <tr key={prediction.driver_id}>
                        <td className="f1-rank">{prediction.latest_position ?? index + 1}</td>
                        <td>
                          <span className="f1-driver">
                            <span style={{ background: color }} />
                            <strong>{prediction.driver_code ?? driverName(prediction.driver_id)}</strong>
                          </span>
                        </td>
                        <td>{prediction.constructor_name ?? prediction.constructor_id ?? "-"}</td>
                        <td>{formatPercent(prediction.points_finish_probability, 0)}</td>
                        <td>{formatPercent(prediction.podium_finish_probability, 0)}</td>
                        <td className={delta && delta < 0 ? "f1-negative" : "f1-positive"}>
                          {delta === null ? "Live" : `${delta > 0 ? "+" : ""}${(delta * 100).toFixed(1)}%`}
                        </td>
                        <td>{prediction.latest_lap_number ?? "-"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <aside className="f1-side-stack">
            <section className="f1-side-panel">
              <span className="f1-kicker">Leader Profile</span>
              <h3>{leader ? driverName(leader.driver_id) : "Awaiting data"}</h3>
              <div className="f1-driver-code">{leader?.driver_code ?? "--"}</div>
              <div className="f1-mini-grid">
                <div>
                  <span>Points</span>
                  <strong>{formatPercent(leader?.points_finish_probability ?? 0, 0)}</strong>
                </div>
                <div>
                  <span>Podium</span>
                  <strong>{formatPercent(leader?.podium_finish_probability ?? 0, 0)}</strong>
                </div>
                <div>
                  <span>Confidence</span>
                  <strong>{formatPercent(leader?.confidence ?? 0, 0)}</strong>
                </div>
                <div>
                  <span>Live Lap</span>
                  <strong>{leader?.latest_lap_number ?? "-"}</strong>
                </div>
              </div>
            </section>

            <section className="f1-side-panel f1-track-panel">
              <div className="f1-panel-header compact">
                <span className="f1-kicker">Circuit</span>
                <strong>{race?.circuit_name ?? "Track map"}</strong>
              </div>
              <svg viewBox="0 0 420 270" role="img" aria-label="Stylized circuit map">
                <path className="track-shadow" d="M70 165 C92 136 119 116 151 108 C189 98 219 110 236 134 C252 157 246 184 216 196 C181 209 128 198 95 174 C76 160 78 140 98 130 C126 116 160 124 187 145 C217 168 252 182 291 178 C335 174 363 149 356 119 C350 92 317 80 286 91 C258 101 239 124 224 149 C204 182 173 214 128 214 C92 214 65 199 59 181 C56 173 61 168 70 165 M226 149 C244 118 269 63 317 67 C349 70 368 91 364 116" />
                <path className="track-line" d="M70 165 C92 136 119 116 151 108 C189 98 219 110 236 134 C252 157 246 184 216 196 C181 209 128 198 95 174 C76 160 78 140 98 130 C126 116 160 124 187 145 C217 168 252 182 291 178 C335 174 363 149 356 119 C350 92 317 80 286 91 C258 101 239 124 224 149 C204 182 173 214 128 214 C92 214 65 199 59 181 C56 173 61 168 70 165 M226 149 C244 118 269 63 317 67 C349 70 368 91 364 116" />
                <circle cx="70" cy="165" r="8" />
                <circle cx="226" cy="149" r="6" />
                <circle cx="317" cy="67" r="6" />
                <circle cx="128" cy="214" r="6" />
              </svg>
            </section>
          </aside>
        </section>

        <section className="f1-lower-grid">
          <div className="f1-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Weekend Sessions</span>
                <h2>Schedule Sync</h2>
              </div>
              <span className="f1-count">{dashboard.freshness?.linked_sessions ?? dashboard.sessions.length} linked</span>
            </div>
            <div className="f1-session-list">
              {dashboard.sessions.map((session) => (
                <div key={session.session_key} className="f1-session-row">
                  <span>{formatDate(session.link?.date_start)}</span>
                  <strong>{session.link?.session_name ?? session.link?.session_type ?? session.session_key}</strong>
                  <small>{session.predictions?.predictions?.length ?? 0} predictions</small>
                </div>
              ))}
            </div>
          </div>

          <div className="f1-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Race Control</span>
                <h2>Live Feed</h2>
              </div>
              <span className="f1-count">{events.length || "sample"}</span>
            </div>
            <div className="f1-event-list">
              {(events.length ? events : latestSession?.events ?? []).slice(0, 6).map((event, index) => (
                <div key={`${eventText(event)}-${index}`} className="f1-event-row">
                  <span>{formatDate(String(event.event_time ?? event.updated_at ?? dashboard.freshness?.latest_event_time ?? ""))}</span>
                  <strong>{eventText(event)}</strong>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </AppShell>
  );
}
