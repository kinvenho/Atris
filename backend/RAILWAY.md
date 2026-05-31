# Railway Backend Setup

Preferred setup: create a Railway service from the GitHub repo and set the service root directory to:

```txt
/backend
```

Set the Railway config file path/source to:

```txt
/backend/railway.json
```

Railway should then start FastAPI with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Fallback setup: if Railway is pointed at the repository root, the root `railway.json`, `requirements.txt`, `Procfile`, `runtime.txt`, and `start.sh` files proxy the deploy into `/backend`.

Required environment variables:

```env
ENV=production
DEBUG=false
CORS_ORIGINS=https://your-vercel-domain.vercel.app
SUPABASE_URL=https://ybokutkaqvppblgonljh.supabase.co
SUPABASE_KEY=your-supabase-service-role-key
XAI_API_KEY=your-xai-api-key
LLM_MODEL=grok-3
LLM_BASE_URL=https://api.x.ai/v1
AGENT_ADMIN_TOKEN=generate-a-long-random-token
```

Cron services:

```bash
python -m app.agent.runner
python -m app.agent.outcome
python -m app.agent.scoring
```

Use the same `/backend` root directory and environment variables for each cron service.
