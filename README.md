```txt
    _  _____ ____  ___ ____
   / \|_   _|  _ \|_ _/ ___|
  / _ \ | | | |_) || |\___ \
 / ___ \| | |  _ < | | ___) |
/_/   \_\_| |_| \_\___|____/
```

# Atris

Atris is becoming a Formula 1 data, analytics, and prediction backend for prediction markets.

The core thesis is simple: F1 is structured enough that the strongest product is not an AI news summarizer. Atris should ingest historical and live race-weekend data, build model-ready features, produce calibrated probabilities, and compare those probabilities against market-implied prices.

The current generic Polymarket agent remains in the codebase, but the product direction is now F1-first:

```txt
F1DataIngestion -> FeatureStore -> PredictionModel -> ProbabilityAPI -> MarketEdgeEngine
```

## Status

Atris V1 backend is deployed on Railway in the reference deployment and writes to Supabase. The deployed service currently runs the original generic Polymarket research loop while the F1 data and prediction layer is designed and implemented.

Recent production runner jobs have completed successfully with:

```txt
markets_scanned: 7
candidates_evaluated: 7
status: success
```

## What Atris Does

The existing generic agent runs this loop:

```txt
MarketScanner -> ContextGatherer -> ProbabilityEngine -> DecisionEngine -> RecommendationWriter
```

Outcome tracking and scoring are separate scheduled jobs.

The agent:

- Fetches active Polymarket markets from the public Gamma API.
- Filters for liquid, active, binary YES/NO markets.
- Uses Grok native web search to gather current context and citations.
- Estimates the probability of the market resolving YES.
- Computes the edge against market-implied probabilities.
- Publishes only when edge and confidence pass thresholds.
- Stores recommendations, evidence, run history, and performance snapshots in Supabase.

The F1 product path will replace AI-first probability generation with a data/model-first system:

- Build a historical F1 warehouse from structured sources.
- Ingest live race-weekend state where practical.
- Generate features for drivers, constructors, circuits, sessions, tires, weather, gaps, pace, penalties, and race-control events.
- Train calibrated models for outcome families such as podium, points finish, race winner, head-to-head, fastest lap, DNF, and safety car.
- Compare model probabilities against Polymarket and later Kalshi market prices.
- Store prediction snapshots with model version, source provenance, and market-edge metadata.

## F1 Data Strategy

Atris should start historical and expand into live data carefully.

Primary data sources under evaluation:

- [F1DB](https://github.com/f1db/f1db): local historical database seed with CSV, JSON, SQL, and SQLite artifacts.
- [Jolpica-F1](https://github.com/jolpica/jolpica-f1): Ergast-compatible historical API for schedules, standings, qualifying, races, laps, pit stops, sprint, and results.
- [FastF1](https://github.com/theOehrly/Fast-F1): Python package for timing, telemetry, session loading, and offline feature generation.
- [OpenF1](https://openf1.org/docs/): historical and real-time F1 API. Historical data is useful immediately; real-time access may require paid access.
- FastF1 live timing / Formula 1 SignalR-derived tooling: potential path to record live sessions into Atris' own server-side feed if we need to avoid depending on a paid live API.

Storage should stay efficient enough for the Supabase free plan during early development:

- Store normalized canonical entities and compact feature snapshots first.
- Keep raw high-frequency telemetry out of Supabase by default.
- Store heavy raw/replay files in local object storage, Supabase Storage, or an external bucket only when needed.
- Use append-only live-event summaries instead of writing every raw car-data tick to Postgres.

## F1 Roadmap

Near-term:

- Seed historical F1 data.
- Add F1 market classification.
- Design efficient Supabase tables for entities, sessions, features, predictions, and market-edge snapshots.
- Build the first model around all high-signal outcome families, starting with the easiest to evaluate historically.

Race-weekend:

- Add scheduled race-weekend ingestion. The backend now has a reusable F1 refresh job for this.
- Record or consume live timing, race-control, weather, position, pit, tire, and gap data.
- Update prediction snapshots as session state changes.

Later:

- Add a full F1 stats and prediction page.
- Add Kalshi support for cross-market pricing.
- Add an explanation layer after model probabilities are already generated.

## Architecture

```txt
backend/
  app/
    main.py
    config.py
    agent/
      runner.py
      scanner.py
      context.py
      probability.py
      decision.py
      writer.py
      outcome.py
      scoring.py
      prompts.py
    integrations/
      polymarket.py
      xai.py
    models/
    routers/
    services/
    supabase/
      schema.sql

frontend/
  app/
  components/
```

Root-level Railway files are present because Railway may build from the repository root:

```txt
railway.json
requirements.txt
runtime.txt
Procfile
start.py
start.sh
```

`start.py` selects the process to run using `ATRIS_PROCESS`.

## Backend API

```http
GET  /
GET  /recommendations
GET  /recommendations/{id}
GET  /performance
GET  /agent/runs
POST /agent/trigger
GET  /f1/sources
GET  /f1/live-readiness
GET  /f1/stored/seasons/{season}/races
GET  /f1/stored/sessions/{session_key}/events
GET  /f1/stored/sessions/{session_key}/driver-snapshots
GET  /f1/predictions/seasons/{season}/rounds/{round}
POST /f1/refresh
POST /f1/ingest/sessions/{session_key}/events
POST /f1/ingest/sessions/{session_key}/driver-snapshots
```

`POST /agent/trigger` and F1 ingestion/refresh endpoints require the `x-atris-admin-token` header in production.

Dry-run example:

```bash
curl -X POST "$ATRIS_API_URL/agent/trigger?dry_run=true" \
  -H "x-atris-admin-token: $AGENT_ADMIN_TOKEN"
```

## Agent Configuration

Defaults live in `backend/app/config.py` and can be overridden with environment variables.

```env
MIN_VOLUME=10000
MIN_LIQUIDITY=5000
MIN_HOURS_TO_CLOSE=48
DEFAULT_CANDIDATES_PER_RUN=7
MAX_CANDIDATES_PER_RUN=10
MIN_EDGE_TO_PUBLISH=0.08
MIN_CONFIDENCE_TO_PUBLISH=0.60
PIPELINE_CADENCE_MINUTES=45
OUTCOME_CHECK_CADENCE_MINUTES=120
LLM_MODEL=grok-3
LLM_BASE_URL=https://api.x.ai/v1
```

## Required Environment Variables

```env
ENV=production
DEBUG=false
CORS_ORIGINS=*
SUPABASE_URL=
SUPABASE_KEY=
XAI_API_KEY=
LLM_MODEL=grok-3
LLM_BASE_URL=https://api.x.ai/v1
AGENT_ADMIN_TOKEN=
DEFAULT_CANDIDATES_PER_RUN=7
F1_REFRESH_SEASON=current
F1_REFRESH_SESSION_LIMIT=250
F1_REFRESH_RETRAIN_MODELS=false
```

Use a Supabase service-role key only on trusted backend services. Do not expose it to the frontend.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Database

The Supabase schema is in:

```txt
backend/supabase/schema.sql
```

Core tables:

- `markets`
- `recommendations`
- `recommendation_evidence`
- `agent_runs`
- `performance_snapshots`

`recommendation_evidence` is kept even if not surfaced in the UI. It is the audit trail for recommendation context.

The planned F1 data model should keep early storage compact enough for the Supabase free plan by storing canonical data, feature snapshots, prediction snapshots, and market-edge snapshots instead of raw high-frequency telemetry.

## Railway Deployment

The main API service uses:

```env
ATRIS_PROCESS=web
```

or omits `ATRIS_PROCESS`, since `web` is the default.

Cron services use the same repo and same environment variables, with only `ATRIS_PROCESS` changed:

```txt
Atris Runner  -> ATRIS_PROCESS=runner
Atris Outcome -> ATRIS_PROCESS=outcome
Atris Scoring -> ATRIS_PROCESS=scoring
Atris F1      -> ATRIS_PROCESS=f1-refresh
```

Recommended schedules:

```txt
runner     */30 * * * *
outcome    0 */2 * * *
scoring    0 0 * * *
f1-refresh 0 */6 * * *
```

The F1 refresh process is idempotent. It refreshes sources, schedule, OpenF1 sessions, compact recent session events, driver session snapshots, race results, qualifying results, feature rows, and model training examples. Model retraining is opt-in with `F1_REFRESH_RETRAIN_MODELS=true` or the `retrain_models=true` query parameter on `POST /f1/refresh`.

## Security Notes

- Do not commit `.env` files.
- Do not expose `SUPABASE_KEY` or any service-role key to the browser.
- Rotate keys if they appear in logs, terminal output, screenshots, or issue reports.
- Keep `AGENT_ADMIN_TOKEN` long, random, and private.
- Public frontend code should call the FastAPI backend, not Supabase directly, for V1.

## Open Source and Commercial Use

Atris can be open source and still be operated as a paid hosted product. The hosted service, infrastructure, data curation, reliability, UI, support, and convenience can be commercial even if the source code is available for self-hosting.

This repository is licensed under MIT. That means others may use, copy, modify, distribute, and run the software, including commercially, as long as they preserve the license and copyright notice.

## License

MIT License. See `LICENSE`.
