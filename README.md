# Atris

Atris is an autonomous market-research backend for Polymarket. It scans active binary markets, gathers current context with Grok web search, estimates Atris' probability of resolution, publishes recommendations when the edge clears configured thresholds, and tracks outcomes over time.

The first production version is intentionally narrow: no accounts, no alerts, no wallet connection, no trade execution, and no portfolio features. Atris V1 is the agent pipeline, database model, API, cron jobs, and a baseline frontend.

## Status

Atris V1 backend is deployed on Railway and writes to Supabase.

Current production API:

```txt
https://atris-production.up.railway.app
```

Recent production runner jobs have completed successfully with:

```txt
markets_scanned: 7
candidates_evaluated: 7
status: success
```

## What Atris Does

Atris runs this loop:

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
```

`POST /agent/trigger` requires the `x-atris-admin-token` header in production.

Dry-run example:

```bash
curl -X POST "https://atris-production.up.railway.app/agent/trigger?dry_run=true" \
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
```

Recommended schedules:

```txt
runner   */30 * * * *
outcome  0 */2 * * *
scoring  0 0 * * *
```

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
