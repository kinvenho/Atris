import AppShell from "@/components/AppShell";
import F1CircuitPanel from "@/components/F1CircuitPanel";
import F1ScrollRail from "@/components/F1ScrollRail";
import Link from "next/link";
import {
  F1DashboardPayload,
  F1DriverSessionSnapshot,
  F1QualifyingResult,
  F1Prediction,
  F1RaceResult,
  F1RaceSummary,
  F1SessionEvent,
  F1SessionRaceLink,
  formatDate,
  formatPercent,
  getF1Dashboard,
  getF1DataCoverage,
  getF1QualifyingResults,
  getF1RaceResults,
  getF1RaceWorkspace,
  getF1SessionRaceLinks,
  getF1StoredRaces,
} from "@/lib/api";
import { driverName } from "@/lib/f1Format";

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

type RaceWorkspaceTab = "overview" | "practice" | "qualifying" | "race" | "results";

const RACE_WORKSPACE_TABS: Array<{ id: RaceWorkspaceTab; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "practice", label: "Practice" },
  { id: "qualifying", label: "Qualifying" },
  { id: "race", label: "Race" },
  { id: "results", label: "Results" },
];

function eventText(event: F1SessionEvent | Record<string, unknown>) {
  const looseEvent = event as Record<string, unknown>;
  return String(looseEvent.message ?? looseEvent.event ?? looseEvent.category ?? looseEvent.event_category ?? "Session update");
}

function eventTime(event: F1SessionEvent) {
  return event.event_time ?? event.updated_at ?? "";
}

function latestEventTime(events: F1SessionEvent[]) {
  return events
    .map((event) => eventTime(event))
    .filter(Boolean)
    .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
}

function probabilityDelta(current: F1Prediction, baseline?: F1Prediction) {
  if (!baseline) return null;
  return current.points_finish_probability - baseline.points_finish_probability;
}

function hexOpacity(hex: string, opacityHex = "66") {
  return /^#[0-9a-fA-F]{6}$/.test(hex) ? `${hex}${opacityHex}` : hex;
}

function raceRound(race: F1RaceSummary) {
  return Number(race.round ?? 0);
}

function raceTimeValue(race: F1RaceSummary) {
  const value = race.race_date ? Date.parse(`${race.race_date}T${race.race_time ?? "00:00:00Z"}`) : NaN;
  return Number.isFinite(value) ? value : 0;
}

function latestStoredRace(races: F1RaceSummary[]) {
  return [...races].sort((a, b) => raceTimeValue(b) - raceTimeValue(a) || raceRound(b) - raceRound(a))[0] ?? null;
}

function commandStoredRace(races: F1RaceSummary[]) {
  const now = Date.now();
  const completedOrCurrent = races
    .filter((race) => raceTimeValue(race) <= now)
    .sort((a, b) => raceTimeValue(b) - raceTimeValue(a) || raceRound(b) - raceRound(a));
  if (completedOrCurrent[0]) return completedOrCurrent[0];
  return [...races].sort((a, b) => raceTimeValue(a) - raceTimeValue(b) || raceRound(a) - raceRound(b))[0] ?? null;
}

function resultPosition(result: F1RaceResult) {
  return result.position_order ?? result.position ?? 99;
}

function qualifyingPosition(result: F1QualifyingResult) {
  return result.qualifying_position ?? 99;
}

function displayPosition(value?: number | string | null) {
  return value === null || value === undefined || value === "" ? "-" : value;
}

function displayMetric(value?: number | string | null, suffix = "") {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return `${numeric.toFixed(numeric >= 100 ? 0 : 3).replace(/\.?0+$/, "")}${suffix}`;
}

function positionGain(start?: number | string | null, finish?: number | string | null) {
  const startPosition = Number(start);
  const finishPosition = Number(finish);
  if (!Number.isFinite(startPosition) || !Number.isFinite(finishPosition) || startPosition <= 0 || finishPosition <= 0) {
    return null;
  }
  return startPosition - finishPosition;
}

function resultConstructorId(result: F1RaceResult) {
  const normalized = (result.constructor_name ?? "").toLowerCase();
  const match = Object.entries(TEAM_COLORS).find(([key]) => normalized.includes(key.replaceAll("_", " ")));
  return match?.[0] ?? "";
}

function resultDriverLabel(result?: F1RaceResult | null) {
  if (!result) return "Awaiting data";
  return result.driver_code ?? driverName(result.driver_id);
}

function qualifyingDriverLabel(result?: F1QualifyingResult | null) {
  if (!result) return "Pending";
  return result.driver_code ?? driverName(result.driver_id);
}

function constructorKey(name?: string | null) {
  return (name ?? "unknown").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function buildRaceTeamSummaries(results: F1RaceResult[]) {
  const teams = new Map<string, {
    id: string;
    name: string;
    drivers: string[];
    points: number;
    bestFinish: number | null;
    rows: number;
  }>();

  for (const result of results) {
    const id = constructorKey(result.constructor_name);
    const row = teams.get(id) ?? {
      id,
      name: result.constructor_name ?? "Unknown",
      drivers: [],
      points: 0,
      bestFinish: null,
      rows: 0,
    };
    const label = resultDriverLabel(result);
    if (!row.drivers.includes(label)) row.drivers.push(label);
    row.points += Number(result.points ?? 0);
    row.rows += 1;
    const position = resultPosition(result);
    if (position !== 99) row.bestFinish = row.bestFinish === null ? position : Math.min(row.bestFinish, position);
    teams.set(id, row);
  }

  return [...teams.values()].sort((a, b) => b.points - a.points || (a.bestFinish ?? 99) - (b.bestFinish ?? 99));
}

function normalizeRaceTab(value?: string): RaceWorkspaceTab {
  return RACE_WORKSPACE_TABS.some((tab) => tab.id === value) ? (value as RaceWorkspaceTab) : "overview";
}

function sessionMatchesTab(session: { link?: { session_name?: string | null; session_type?: string | null } }, tab: RaceWorkspaceTab) {
  const label = `${session.link?.session_name ?? ""} ${session.link?.session_type ?? ""}`.toLowerCase();
  if (tab === "practice") return label.includes("practice");
  if (tab === "qualifying") return label.includes("qualifying");
  if (tab === "race") return label.includes("race");
  return false;
}

function sessionLinkMatchesTab(session: F1SessionRaceLink, tab: RaceWorkspaceTab) {
  const label = `${session.session_name ?? ""} ${session.session_type ?? ""}`.toLowerCase();
  if (tab === "practice") return label.includes("practice");
  if (tab === "qualifying") return label.includes("qualifying");
  if (tab === "race") return label.includes("race");
  return false;
}

function dashboardSessionDate(session: F1DashboardPayload["sessions"][number]) {
  return session.link?.date_start ?? session.link?.metadata?.session_date_start ?? null;
}

function snapshotMetric(snapshot: F1DriverSessionSnapshot, key: string) {
  const value = snapshot.metrics?.[key];
  return typeof value === "number" || typeof value === "string" ? value : null;
}

function numericSnapshotMetric(snapshot: F1DriverSessionSnapshot, key: string) {
  const value = snapshotMetric(snapshot, key);
  if (value === null) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function telemetryValue(snapshot: F1DriverSessionSnapshot, key: string, suffix = "") {
  const value = snapshotMetric(snapshot, key);
  if (value === null) return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return `${numeric.toFixed(Math.abs(numeric) >= 100 ? 0 : 2).replace(/\.?0+$/, "")}${suffix}`;
}

function telemetryPercent(snapshot: F1DriverSessionSnapshot, key: string) {
  const value = numericSnapshotMetric(snapshot, key);
  if (value === null) return "-";
  return `${Math.round(Math.min(100, Math.max(0, value)))}%`;
}

function latestTelemetryRows(rows: Array<{
  session: F1DashboardPayload["sessions"][number];
  snapshot: F1DriverSessionSnapshot;
  result?: F1RaceResult;
  prediction?: F1Prediction;
}>) {
  const byDriver = new Map<string, {
    session: F1DashboardPayload["sessions"][number];
    snapshot: F1DriverSessionSnapshot;
    result?: F1RaceResult;
    prediction?: F1Prediction;
  }>();
  for (const row of rows) {
    const driverKey = String(row.snapshot.driver_number ?? row.prediction?.driver_number ?? row.result?.driver_number ?? "");
    if (!driverKey) continue;
    const current = byDriver.get(driverKey);
    const currentLap = Number(current?.snapshot.latest_lap_number ?? current?.snapshot.lap_count ?? -1);
    const nextLap = Number(row.snapshot.latest_lap_number ?? row.snapshot.lap_count ?? -1);
    if (!current || nextLap >= currentLap) byDriver.set(driverKey, row);
  }
  return [...byDriver.values()].sort((a, b) => Number(a.snapshot.latest_position ?? 99) - Number(b.snapshot.latest_position ?? 99));
}

type F1CommandCenterProps = {
  season?: number;
  round?: number;
  mode?: "overview" | "race";
  activeTab?: string;
};

export default async function F1CommandCenter({ season: requestedSeason, round: requestedRound, mode = "overview", activeTab }: F1CommandCenterProps = {}) {
  const currentSeason = new Date().getFullYear();
  const coverage = requestedSeason ? [] : await getF1DataCoverage();
  const latestStoredSeason = coverage[0]?.season ?? 2024;
  const season = requestedSeason ?? (mode === "overview" ? currentSeason : latestStoredSeason);
  const storedRaces = mode === "overview" ? await getF1StoredRaces(season) : [];
  const overviewRaces = storedRaces
    .filter((raceItem) => Number(raceItem.season ?? season) === season)
    .sort((a, b) => raceRound(a) - raceRound(b))
    .slice(0, 8);
  const seasonRaces = storedRaces.filter((raceItem) => Number(raceItem.season ?? season) === season);
  const commandRace = commandStoredRace(seasonRaces);
  const round = requestedRound ?? raceRound(commandRace ?? overviewRaces[0] ?? { round: 1 });
  const [dashboardPayload, workspace] = await Promise.all([
    getF1Dashboard(season, round),
    mode === "race" ? getF1RaceWorkspace(season, round) : Promise.resolve(null),
  ]);
  const dashboard: F1DashboardPayload = dashboardPayload ?? {
    season,
    round,
    race: null,
    sessions: [],
    pre_race_predictions: null,
    latest_race_weekend_predictions: null,
    freshness: {},
  };
  const roundRaceResults = workspace?.race_results ?? (mode === "race" ? await getF1RaceResults(season, round) : []);
  const roundQualifyingResults = workspace?.qualifying_results ?? (mode === "race" ? await getF1QualifyingResults(season, round) : []);
  const roundSessionLinks = workspace?.session_links ?? (mode === "race" ? await getF1SessionRaceLinks(season, round) : []);
  const storedRaceResults = mode === "race" && !roundRaceResults.length ? await getF1RaceResults(season) : roundRaceResults;
  const storedQualifyingResults = mode === "race" && !roundQualifyingResults.length ? await getF1QualifyingResults(season) : roundQualifyingResults;
  const storedSessionLinks = mode === "race" && !roundSessionLinks.length ? await getF1SessionRaceLinks(season) : roundSessionLinks;
  const raceResults = storedRaceResults
    .filter((result) => Number(result.round) === round)
    .sort((a, b) => resultPosition(a) - resultPosition(b))
    .slice(0, 10);
  const podiumResults = raceResults.slice(0, 3);
  const qualifyingResults = storedQualifyingResults
    .filter((result) => Number(result.round) === round)
    .sort((a, b) => qualifyingPosition(a) - qualifyingPosition(b))
    .slice(0, 10);
  const qualifyingByDriver = new Map(
    qualifyingResults.map((result) => [result.driver_id, result]),
  );
  const resultByDriverNumber = new Map(
    raceResults.map((result) => [String(result.driver_number ?? ""), result]),
  );
  const race = dashboard.race ?? workspace?.race ?? null;
  const liveBoard = dashboard.latest_race_weekend_predictions ?? dashboard.pre_race_predictions;
  const preRaceByDriver = new Map(
    (dashboard.pre_race_predictions?.predictions ?? []).map((prediction) => [prediction.driver_id, prediction]),
  );
  const predictions = [...(liveBoard?.predictions ?? [])].sort(
    (a, b) => Number(b.points_finish_probability || 0) - Number(a.points_finish_probability || 0),
  );
  const predictionByDriverNumber = new Map(
    predictions.map((prediction) => [String(prediction.driver_number ?? ""), prediction]),
  );
  const leader = predictions[0];
  const raceWinner = raceResults[0];
  const poleSitter = qualifyingResults[0];
  const fastestLap = raceResults.find((result) => Number(result.fastest_lap_rank) === 1);
  const raceLeaderName = leader ? driverName(leader.driver_id) : resultDriverLabel(raceWinner);
  const raceLeaderCode = leader?.driver_code ?? raceWinner?.driver_code ?? "--";
  const raceLeaderTeam = leader?.constructor_name ?? raceWinner?.constructor_name ?? "Field";
  const raceLeaderStatus = leader ? "Prediction Leader" : raceWinner ? "Race Winner" : "Awaiting data";
  const teamSummaries = buildRaceTeamSummaries(raceResults);
  const topTeam = teamSummaries[0];
  const fieldStack = predictions.slice(0, 5);
  const allEvents = dashboard.sessions.flatMap((session) => session.events ?? []);
  const latestRaceControlTime = latestEventTime(allEvents);
  const events = [...allEvents]
    .sort((a, b) => Date.parse(eventTime(b)) - Date.parse(eventTime(a)))
    .slice(0, 8);
  const isRaceWorkspace = mode === "race";
  const selectedTab = isRaceWorkspace ? normalizeRaceTab(activeTab) : "overview";
  const selectedSessions = selectedTab === "practice" || selectedTab === "qualifying" || selectedTab === "race"
    ? dashboard.sessions.filter((session) => sessionMatchesTab(session, selectedTab))
    : [];
  const selectedSessionLinks = selectedTab === "practice" || selectedTab === "qualifying" || selectedTab === "race"
    ? storedSessionLinks.filter((session) => Number(session.round) === round && sessionLinkMatchesTab(session, selectedTab))
    : [];
  const selectedSessionRows = [
    ...selectedSessions.map((session) => ({
      key: session.session_key,
      date: dashboardSessionDate(session),
      name: session.link?.session_name ?? session.link?.session_type ?? String(session.session_key),
      events: session.events?.length ?? 0,
      snapshots: session.driver_snapshots?.length ?? 0,
      predictions: session.predictions?.predictions?.length ?? 0,
      confidence: null as number | null,
    })),
    ...selectedSessionLinks
      .filter((link) => !selectedSessions.some((session) => session.session_key === link.session_key))
      .map((link) => ({
        key: link.session_key,
        date: link.metadata?.session_date_start ?? link.metadata?.race_date,
        name: link.session_name ?? link.session_type ?? String(link.session_key),
        events: 0,
        snapshots: 0,
        predictions: 0,
        confidence: link.confidence ?? null,
      })),
  ];
  const selectedTelemetryRows = selectedSessions
    .flatMap((session) => (session.driver_snapshots ?? []).map((snapshot) => ({
      session,
      snapshot,
      result: resultByDriverNumber.get(String(snapshot.driver_number ?? "")),
      prediction: predictionByDriverNumber.get(String(snapshot.driver_number ?? "")),
    })))
    .sort((a, b) => Number(a.snapshot.latest_position ?? 99) - Number(b.snapshot.latest_position ?? 99));
  const visualiserRows = latestTelemetryRows(selectedTelemetryRows);
  const rowsWithLocation = visualiserRows.filter((row) => (
    numericSnapshotMetric(row.snapshot, "location_x") !== null
    && numericSnapshotMetric(row.snapshot, "location_y") !== null
  ));
  const fastestTelemetryRow = visualiserRows
    .filter((row) => Number(row.snapshot.fastest_lap_duration ?? Infinity) > 0)
    .sort((a, b) => Number(a.snapshot.fastest_lap_duration ?? Infinity) - Number(b.snapshot.fastest_lap_duration ?? Infinity))[0];
  const selectedSessionEvents = selectedSessions
    .flatMap((session) => (session.events ?? []).map((event) => ({ session, event })))
    .sort((a, b) => Date.parse(eventTime(b.event)) - Date.parse(eventTime(a.event)))
    .slice(0, 12);
  const raceSessionRows = [
    ...dashboard.sessions.map((session) => ({
      key: session.session_key,
      date: dashboardSessionDate(session),
      name: session.link?.session_name ?? session.link?.session_type ?? String(session.session_key),
      events: session.events?.length ?? 0,
      snapshots: session.driver_snapshots?.length ?? 0,
      predictions: session.predictions?.predictions?.length ?? 0,
      confidence: null as number | null,
    })),
    ...storedSessionLinks
      .filter((link) => Number(link.round) === round && !dashboard.sessions.some((session) => session.session_key === link.session_key))
      .map((link) => ({
        key: link.session_key,
        date: link.metadata?.session_date_start ?? link.metadata?.race_date,
        name: link.session_name ?? link.session_type ?? String(link.session_key),
        events: 0,
        snapshots: 0,
        predictions: 0,
        confidence: link.confidence ?? null,
      })),
  ];
  const coverageItems = isRaceWorkspace
    ? [
        { label: "Winner", value: resultDriverLabel(raceWinner) },
        { label: "Pole", value: qualifyingDriverLabel(poleSitter) },
        { label: "Fastest Lap", value: fastestLap ? `${resultDriverLabel(fastestLap)} ${fastestLap.fastest_lap_time ?? ""}`.trim() : "Pending" },
        { label: "Classified", value: raceResults.length ? `${raceResults.length} rows` : "Pending" },
      ]
    : [
        { label: "Current Event", value: race?.race_name ?? `${season} pending` },
        { label: "Sessions", value: dashboard.sessions.length ? `${dashboard.sessions.length} linked` : "Pending" },
        { label: "Race Control", value: allEvents.length ? `${allEvents.length} events` : "Pending" },
        { label: "Predictions", value: predictions.length ? `${predictions.length} drivers` : "Pending" },
      ];
  const teamAccent = TEAM_COLORS[raceWinner?.constructor_id ?? ""] ?? "#85868a";

  return (
    <AppShell>
      <main className="f1-page">
        <section className="f1-hero">
          <div className="f1-context">
            <span className="f1-pill">{isRaceWorkspace ? "Race File" : "F1 Command"}</span>
            <span>Round {dashboard.round}</span>
            <span>{dashboard.season}</span>
            <span>{race?.country ?? "Race weekend"}</span>
          </div>
          <div className="f1-hero-grid">
            <div>
              <h1 className="f1-title">{isRaceWorkspace ? race?.race_name ?? "Grand Prix" : race?.race_name ?? "Command"}</h1>
              {isRaceWorkspace ? (
                <nav className="f1-breadcrumb" aria-label="F1 race breadcrumbs">
                  <Link href="/">Command</Link>
                  <Link href="/f1/races">Races</Link>
                  <span>{race?.circuit_name ?? "Circuit"}</span>
                  <span>{race?.locality ?? "Race model"}</span>
                  <span>{liveBoard?.feature_set ?? "race_weekend_v1"}</span>
                </nav>
              ) : (
                <div className="f1-command-statusline">
                  <span>Command Root</span>
                  <span>Round {dashboard.round}</span>
                  <span>{race?.locality ?? race?.country ?? `${season} feed`}</span>
                  <span>{dashboard.sessions.length ? "OpenF1 linked" : "OpenF1 sync pending"}</span>
                </div>
              )}
            </div>
            <div className="f1-race-clock">
              <span>{isRaceWorkspace ? "Latest Build" : "Latest Event"}</span>
              <strong>{formatDate(isRaceWorkspace ? dashboard.freshness?.built_at : latestRaceControlTime ?? dashboard.freshness?.built_at)}</strong>
              <small>{dashboard.freshness?.race_weekend_prediction_count ?? predictions.length} race-weekend predictions</small>
            </div>
          </div>
        </section>

        <section className="f1-data-strip">
          {coverageItems.map((item) => (
            <div key={item.label} className="f1-data-tile">
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </section>

        {isRaceWorkspace ? (
          <nav className="f1-tabbar" aria-label="Race workspace sections">
            {RACE_WORKSPACE_TABS.map((tab) => {
              const href = tab.id === "overview"
                ? `/f1/races/${season}/${round}`
                : `/f1/races/${season}/${round}?tab=${tab.id}`;
              return (
                <Link key={tab.id} href={href} className={selectedTab === tab.id ? "active" : ""}>
                  {tab.label}
                </Link>
              );
            })}
          </nav>
        ) : null}

        {!isRaceWorkspace ? (
          <section className="f1-main-panel f1-overview-rail">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Race Directory</span>
                <h2>Season Command Rail</h2>
              </div>
              <Link href="/f1/races" className="f1-command-link">
                All Races
              </Link>
            </div>
            <F1ScrollRail ariaLabel="Season command race rail" contentClassName="f1-overview-races">
              {overviewRaces.length ? overviewRaces.map((raceItem) => {
                const itemRound = raceRound(raceItem);
                const isSelected = itemRound === dashboard.round;
                return (
                  <Link
                    key={`${raceItem.season ?? season}-${itemRound}`}
                    href={`/f1/races/${raceItem.season ?? season}/${itemRound}`}
                    className={isSelected ? "f1-overview-race active" : "f1-overview-race"}
                  >
                    <span>R{itemRound}</span>
                    <strong>{raceItem.race_name ?? "Grand Prix"}</strong>
                    <small>{raceItem.country ?? raceItem.locality ?? "Race file"}</small>
                  </Link>
                );
              }) : (
                <div className="f1-rail-empty">
                  <span>Current Season Pending</span>
                  <strong>No {season} race schedule is stored yet. Command is waiting for the OpenF1/current-season sync.</strong>
                </div>
              )}
            </F1ScrollRail>
          </section>
        ) : null}

        {(!isRaceWorkspace || selectedTab === "overview") ? (
        <section className="f1-command-grid">
          <div className="f1-main-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">{predictions.length ? "Prediction Board" : "Race Classification"}</span>
                <h2>{predictions.length ? "Points Finish Control" : "Stored Result Control"}</h2>
              </div>
              <div className="f1-status">
                <span className="f1-live-dot" />
                {predictions.length ? liveBoard?.prediction_mode ?? "pending" : raceResults.length ? "stored_results" : "pending"}
              </div>
            </div>

            {predictions.length ? (
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
            ) : raceResults.length ? (
            <div className="f1-table-wrap">
              <table className="f1-table">
                <thead>
                  <tr>
                    <th>Pos.</th>
                    <th>Driver</th>
                    <th>Team</th>
                    <th>Grid</th>
                    <th>Q Pos.</th>
                    <th>Gain</th>
                    <th>Pts.</th>
                    <th>FL</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {raceResults.map((result) => {
                    const qualifying = qualifyingByDriver.get(result.driver_id);
                    const gain = positionGain(result.grid, result.position_order ?? result.position);
                    return (
                      <tr key={result.driver_id}>
                        <td className="f1-rank">{result.position_text ?? result.position ?? result.position_order ?? "-"}</td>
                        <td>
                          <strong>{resultDriverLabel(result)}</strong>
                        </td>
                        <td>{result.constructor_name ?? "-"}</td>
                        <td>{displayPosition(result.grid)}</td>
                        <td>{displayPosition(qualifying?.qualifying_position)}</td>
                        <td className={gain === null || gain >= 0 ? "f1-positive" : "f1-negative"}>
                          {gain === null ? "-" : gain > 0 ? `+${gain}` : gain}
                        </td>
                        <td>{result.points ?? 0}</td>
                        <td>{result.fastest_lap_time ?? "-"}</td>
                        <td>{result.status ?? result.race_time ?? "-"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            ) : (
              <div className="f1-empty-panel">
                <span>Race Layer Empty</span>
                <strong>No prediction or classification rows are available from the API for this race yet.</strong>
              </div>
            )}
          </div>

          <aside className="f1-side-stack">
            <section className="f1-side-panel">
              <div className="f1-panel-header inline">
                <span className="f1-kicker">{raceLeaderStatus}</span>
                <strong>{raceLeaderTeam}</strong>
              </div>
              <h3>{raceLeaderName}</h3>
              <div className="f1-driver-code">{raceLeaderCode}</div>
              <div className="f1-mini-grid">
                {leader ? (
                  <>
                    <div>
                      <span>Points</span>
                      <strong>{formatPercent(leader.points_finish_probability, 0)}</strong>
                    </div>
                    <div>
                      <span>Podium</span>
                      <strong>{formatPercent(leader.podium_finish_probability, 0)}</strong>
                    </div>
                    <div>
                      <span>Confidence</span>
                      <strong>{formatPercent(leader.confidence ?? 0, 0)}</strong>
                    </div>
                    <div>
                      <span>Live Lap</span>
                      <strong>{leader.latest_lap_number ?? "-"}</strong>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <span>Finish</span>
                      <strong>{raceWinner?.position_text ?? raceWinner?.position ?? raceWinner?.position_order ?? "-"}</strong>
                    </div>
                    <div>
                      <span>Points</span>
                      <strong>{raceWinner?.points ?? 0}</strong>
                    </div>
                    <div>
                      <span>Grid</span>
                      <strong>{displayPosition(raceWinner?.grid)}</strong>
                    </div>
                    <div>
                      <span>Laps</span>
                      <strong>{raceWinner?.laps ?? "-"}</strong>
                    </div>
                  </>
                )}
              </div>
            </section>

            {!isRaceWorkspace ? (
              <section className="f1-side-panel f1-field-panel">
                <div className="f1-panel-header compact">
                  <span className="f1-kicker">Field Stack</span>
                  <strong>Top {fieldStack.length}</strong>
                </div>
                <div className="f1-field-bars">
                  {fieldStack.map((prediction) => {
                    const color = TEAM_COLORS[prediction.constructor_id ?? ""] ?? "#ff2d2d";
                    const probability = Math.round(Number(prediction.points_finish_probability || 0) * 100);
                    return (
                      <div key={prediction.driver_id} className="f1-field-bar-row">
                        <div
                          className="f1-field-bar-fill"
                          aria-label={`${prediction.driver_code ?? prediction.driver_id} points probability ${probability}%`}
                          style={{
                            width: `${probability}%`,
                            backgroundColor: hexOpacity(color),
                            borderRightColor: color,
                          }}
                        >
                          <strong>{prediction.driver_code ?? driverName(prediction.driver_id)}</strong>
                          <span>{probability}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ) : (
              <section className="f1-side-panel">
                <div className="f1-team-accent" style={{ borderColor: teamAccent }}>
                  <span style={{ background: teamAccent }} />
                  <strong>{topTeam?.name ?? raceLeaderTeam}</strong>
                </div>
                <div className="f1-panel-header compact">
                  <span className="f1-kicker">Team Data</span>
                  <strong>{topTeam ? topTeam.name : "Pending"}</strong>
                </div>
                <div className="f1-source-card-body">
                  <div>
                    <span>Top Team Points</span>
                    <strong>{topTeam ? topTeam.points : "Pending"}</strong>
                  </div>
                  <div>
                    <span>Best Finish</span>
                    <strong>{topTeam?.bestFinish ?? "Pending"}</strong>
                  </div>
                  <div>
                    <span>Drivers</span>
                    <strong>{topTeam ? topTeam.drivers.join(" / ") : "Pending classification"}</strong>
                  </div>
                </div>
              </section>
            )}

            <F1CircuitPanel circuitName={race?.circuit_name} />
          </aside>
        </section>
        ) : null}

        {isRaceWorkspace && selectedTab !== "overview" && selectedTab !== "results" && selectedTab !== "qualifying" ? (
          <section className="f1-main-panel f1-session-detail-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Session View</span>
                <h2>{selectedTab} Layer</h2>
              </div>
              <div className="f1-status">
                <span className="f1-live-dot" />
                {selectedSessionRows.length ? `${selectedSessionRows.length}_sessions` : "pending"}
              </div>
            </div>
            {selectedSessionRows.length ? (
              <div className="f1-session-data-grid">
                <div className="f1-session-detail-list">
                  {selectedSessionRows.map((session) => (
                    <div key={session.key} className="f1-session-detail-row">
                      <span>{formatDate(session.date)}</span>
                      <strong>{session.name}</strong>
                      <small>{session.events} events</small>
                      <small>{session.snapshots} driver snapshots</small>
                      <small>{session.predictions} predictions</small>
                      {session.confidence !== null ? <small>{formatPercent(session.confidence, 0)} match</small> : null}
                    </div>
                  ))}
                </div>

                {selectedTab === "race" ? (
                  <div className="f1-visualiser-grid">
                    <section className="f1-visualiser-panel">
                      <div className="f1-panel-header compact">
                        <span className="f1-kicker">Track Visualiser</span>
                        <strong>{rowsWithLocation.length ? `${rowsWithLocation.length} cars` : "Location pending"}</strong>
                      </div>
                      {rowsWithLocation.length ? (
                        <div className="f1-track-radar" aria-label="Latest stored car positions">
                          {rowsWithLocation.slice(0, 20).map((row) => {
                            const x = numericSnapshotMetric(row.snapshot, "location_x") ?? 0;
                            const y = numericSnapshotMetric(row.snapshot, "location_y") ?? 0;
                            const left = Math.max(4, Math.min(96, ((x + 10000) / 20000) * 100));
                            const top = Math.max(4, Math.min(96, ((y + 10000) / 20000) * 100));
                            const label = row.result?.driver_code ?? row.prediction?.driver_code ?? `#${row.snapshot.driver_number}`;
                            return (
                              <span
                                key={`${row.snapshot.session_key}-${row.snapshot.driver_number}-map`}
                                className="f1-car-dot"
                                style={{ left: `${left}%`, top: `${top}%` }}
                                title={label}
                              >
                                {label}
                              </span>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="f1-empty-panel compact">
                          <span>Coordinate Stream Empty</span>
                          <strong>OpenF1 has no stored location rows for this session window yet.</strong>
                        </div>
                      )}
                    </section>

                    <section className="f1-visualiser-panel">
                      <div className="f1-panel-header compact">
                        <span className="f1-kicker">Race Timing</span>
                        <strong>{fastestTelemetryRow ? "Fastest lap stored" : "Timing pending"}</strong>
                      </div>
                      <div className="f1-timing-board">
                        <div>
                          <span>Fastest Lap</span>
                          <strong>{fastestTelemetryRow ? displayMetric(fastestTelemetryRow.snapshot.fastest_lap_duration, "s") : "-"}</strong>
                          <small>{fastestTelemetryRow?.result?.driver_code ?? fastestTelemetryRow?.prediction?.driver_code ?? "No row"}</small>
                        </div>
                        <div>
                          <span>Latest Lap</span>
                          <strong>{visualiserRows[0]?.snapshot.latest_lap_number ?? "-"}</strong>
                          <small>{visualiserRows.length} driver snapshots</small>
                        </div>
                        <div>
                          <span>Pit Feed</span>
                          <strong>{visualiserRows.reduce((total, row) => total + Number(numericSnapshotMetric(row.snapshot, "pit_stops") ?? 0), 0)}</strong>
                          <small>stored stops</small>
                        </div>
                      </div>
                    </section>
                  </div>
                ) : null}

                {selectedTelemetryRows.length ? (
                  <div className="f1-table-wrap">
                    <table className="f1-table f1-telemetry-table">
                      <thead>
                        <tr>
                          <th>Pos.</th>
                          <th>Driver</th>
                          <th>Gap</th>
                          <th>Int.</th>
                          <th>Lap</th>
                          <th>Fastest</th>
                          <th>Last</th>
                          <th>S1</th>
                          <th>S2</th>
                          <th>S3</th>
                          <th>Speed</th>
                          <th>Tyre</th>
                          <th>Pit</th>
                          <th>Throttle</th>
                          <th>Brake</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedTelemetryRows.slice(0, 22).map(({ snapshot, result, prediction }) => {
                          const driverCode = result?.driver_code ?? prediction?.driver_code ?? `#${snapshot.driver_number}`;
                          return (
                            <tr key={`${snapshot.session_key}-${snapshot.driver_number}`}>
                              <td className="f1-rank">{displayPosition(snapshot.latest_position)}</td>
                              <td>
                                <strong>{driverCode}</strong>
                              </td>
                              <td>{telemetryValue(snapshot, "gap_to_leader")}</td>
                              <td>{telemetryValue(snapshot, "interval")}</td>
                              <td>{displayPosition(snapshot.latest_lap_number ?? snapshot.lap_count)}</td>
                              <td>{displayMetric(snapshot.fastest_lap_duration, "s")}</td>
                              <td>{displayMetric(snapshotMetric(snapshot, "latest_lap_duration"), "s")}</td>
                              <td>{displayMetric(snapshotMetric(snapshot, "duration_sector_1"), "s")}</td>
                              <td>{displayMetric(snapshotMetric(snapshot, "duration_sector_2"), "s")}</td>
                              <td>{displayMetric(snapshotMetric(snapshot, "duration_sector_3"), "s")}</td>
                              <td>{telemetryValue(snapshot, "latest_speed", " kph")}</td>
                              <td>{snapshotMetric(snapshot, "compound") ?? "-"}</td>
                              <td>{telemetryValue(snapshot, "pit_stops")}</td>
                              <td>{telemetryPercent(snapshot, "latest_throttle")}</td>
                              <td>{telemetryPercent(snapshot, "latest_brake")}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="f1-empty-panel">
                    <span>Telemetry Pending</span>
                    <strong>Session links exist, but driver snapshot rows are not stored yet for this tab.</strong>
                  </div>
                )}

                {selectedSessionEvents.length ? (
                  <div className="f1-race-control-feed">
                    <div className="f1-panel-header compact">
                      <span className="f1-kicker">Race Control</span>
                      <strong>{selectedSessionEvents.length} latest</strong>
                    </div>
                    <div className="f1-event-list">
                      {selectedSessionEvents.map(({ event }, index) => (
                        <div key={`${event.event_time}-${event.message}-${index}`} className="f1-event-row">
                          <span>{formatDate(eventTime(event))}</span>
                          <strong>{eventText(event)}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="f1-empty-panel">
                <span>Session Pending</span>
                <strong>No stored {selectedTab} sessions are linked for this race yet.</strong>
              </div>
            )}
          </section>
        ) : null}

        {isRaceWorkspace && selectedTab === "qualifying" ? (
          <section className="f1-main-panel f1-classification-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Qualifying Result</span>
                <h2>Grid Formation</h2>
              </div>
              <div className="f1-status">
                <span className="f1-live-dot" />
                {qualifyingResults.length ? "stored_qualifying" : selectedSessionRows.length ? "session_linked" : "pending"}
              </div>
            </div>
            {qualifyingResults.length ? (
              <div className="f1-table-wrap">
                <table className="f1-table f1-classification-table">
                  <thead>
                    <tr>
                      <th>Pos.</th>
                      <th>Driver</th>
                      <th>Team</th>
                      <th>Q1</th>
                      <th>Q2</th>
                      <th>Q3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {qualifyingResults.map((result) => (
                      <tr key={result.driver_id}>
                        <td className="f1-rank">{result.qualifying_position ?? "-"}</td>
                        <td>
                          <strong>{result.driver_code ?? driverName(result.driver_id)}</strong>
                        </td>
                        <td>{result.constructor_name ?? "-"}</td>
                        <td>{result.q1 ?? "-"}</td>
                        <td>{result.q2 ?? "-"}</td>
                        <td>{result.q3 ?? "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : selectedSessionRows.length ? (
              <>
                <div className="f1-empty-panel">
                  <span>Session Linked</span>
                  <strong>Qualifying is linked to this race, but detailed classification rows are not stored yet.</strong>
                </div>
                <div className="f1-session-detail-list">
                  {selectedSessionRows.map((session) => (
                    <div key={session.key} className="f1-session-detail-row">
                      <span>{formatDate(session.date)}</span>
                      <strong>{session.name}</strong>
                      <small>{session.events} events</small>
                      <small>{session.snapshots} driver snapshots</small>
                      <small>{session.predictions} predictions</small>
                      {session.confidence !== null ? <small>{formatPercent(session.confidence, 0)} match</small> : null}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="f1-empty-panel">
                <span>Qualifying Pending</span>
                <strong>No stored qualifying classification is available yet for this round.</strong>
              </div>
            )}
          </section>
        ) : null}

        {(!isRaceWorkspace || selectedTab === "overview") ? (
        <section className="f1-lower-grid">
          <div className="f1-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Weekend Sessions</span>
                <h2>Schedule Sync</h2>
              </div>
              <span className="f1-count">{raceSessionRows.length} linked</span>
            </div>
            {raceSessionRows.length ? (
            <div className="f1-session-list">
              {raceSessionRows.slice(0, 8).map((session) => (
                <div key={session.key} className="f1-session-row">
                  <span>{formatDate(session.date)}</span>
                  <strong>{session.name}</strong>
                  <small>
                    {session.events || session.snapshots || session.predictions
                      ? `${session.events} events / ${session.snapshots} snapshots / ${session.predictions} predictions`
                      : session.confidence !== null
                        ? `${formatPercent(session.confidence, 0)} match, detail feed pending`
                        : "detail feed pending"}
                  </small>
                </div>
              ))}
            </div>
            ) : (
              <div className="f1-empty-panel">
                <span>Sessions Pending</span>
                <strong>No stored session links are available from the API for this race yet.</strong>
              </div>
            )}
          </div>

          <div className="f1-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">{isRaceWorkspace ? "Constructor Result" : "Race Control"}</span>
                <h2>{isRaceWorkspace ? "Race Team Stack" : "Live Feed"}</h2>
              </div>
              <span className="f1-count">{isRaceWorkspace ? teamSummaries.length : events.length}</span>
            </div>
            {isRaceWorkspace && teamSummaries.length ? (
            <div className="f1-session-list">
              {teamSummaries.slice(0, 6).map((team) => (
                <div key={team.id} className="f1-session-row">
                  <span>{team.points} pts</span>
                  <strong>{team.name}</strong>
                  <small>P{team.bestFinish ?? "-"} best / {team.drivers.join(" / ")}</small>
                </div>
              ))}
            </div>
            ) : events.length ? (
            <div className="f1-event-list">
              {events.slice(0, 6).map((event, index) => (
                <div key={`${eventText(event)}-${index}`} className="f1-event-row">
                  <span>{formatDate(String(event.event_time ?? event.updated_at ?? dashboard.freshness?.latest_event_time ?? ""))}</span>
                  <strong>{eventText(event)}</strong>
                </div>
              ))}
            </div>
            ) : (
              <div className="f1-empty-panel">
                <span>{isRaceWorkspace ? "Team Result Pending" : "Race Control Empty"}</span>
                <strong>
                  {isRaceWorkspace
                    ? "No constructor result rows are available from the API for this race yet."
                    : "No live event rows are available from the API yet."}
                </strong>
              </div>
            )}
          </div>
        </section>
        ) : null}

        {isRaceWorkspace && selectedTab === "results" ? (
          <section className="f1-main-panel f1-classification-panel">
            <div className="f1-panel-header">
              <div>
                <span className="f1-kicker">Race Result</span>
                <h2>Classification</h2>
              </div>
              <div className="f1-status">
                <span className="f1-live-dot" />
                {raceResults.length ? "stored_results" : "pending"}
              </div>
            </div>
            {raceResults.length ? (
              <>
                <div className="f1-podium">
                  {[podiumResults[1], podiumResults[0], podiumResults[2]].filter(Boolean).map((result) => {
                    const finishPosition = Number(result.position_order ?? result.position ?? 0);
                    const constructorId = resultConstructorId(result);
                    const color = TEAM_COLORS[constructorId] ?? "#ff1801";
                    return (
                      <div
                        key={result.driver_id}
                        className={`f1-podium-step position-${finishPosition}`}
                        style={{
                          backgroundColor: hexOpacity(color, "66"),
                          borderTopColor: color,
                        }}
                      >
                        <strong>{finishPosition || result.position_text || "-"}</strong>
                        <span>{result.driver_code ?? driverName(result.driver_id)}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="f1-table-wrap">
                  <table className="f1-table f1-classification-table">
                    <thead>
                      <tr>
                        <th>Pos.</th>
                        <th>Driver</th>
                        <th>Team</th>
                        <th>Start</th>
                        <th>Q Pos.</th>
                        <th>Gain</th>
                        <th>Pts.</th>
                        <th>FL</th>
                        <th>Laps</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {raceResults.map((result) => {
                        const qualifying = qualifyingByDriver.get(result.driver_id);
                        const gain = positionGain(result.grid, result.position_order ?? result.position);
                        return (
                          <tr key={result.driver_id}>
                            <td className="f1-rank">{result.position_text ?? result.position ?? result.position_order ?? "-"}</td>
                            <td>
                              <strong>{result.driver_code ?? driverName(result.driver_id)}</strong>
                            </td>
                            <td>{result.constructor_name ?? "-"}</td>
                            <td>{displayPosition(result.grid)}</td>
                            <td>{displayPosition(qualifying?.qualifying_position)}</td>
                            <td className={gain === null || gain >= 0 ? "f1-positive" : "f1-negative"}>
                              {gain === null ? "-" : gain > 0 ? `+${gain}` : gain}
                            </td>
                            <td>{result.points ?? 0}</td>
                            <td>{result.fastest_lap_time ?? "-"}</td>
                            <td>{result.laps ?? "-"}</td>
                            <td>{result.status ?? result.race_time ?? "-"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="f1-empty-panel">
                <span>Classification Pending</span>
                <strong>Stored race results are not available yet for this round.</strong>
              </div>
            )}
          </section>
        ) : null}
      </main>
    </AppShell>
  );
}
