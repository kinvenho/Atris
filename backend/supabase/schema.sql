create extension if not exists pgcrypto;

create table if not exists public.markets (
    id uuid primary key default gen_random_uuid(),
    polymarket_id text not null unique,
    question text not null,
    category text,
    closing_time timestamptz not null,
    created_at timestamptz not null default now()
);

create table if not exists public.recommendations (
    id uuid primary key default gen_random_uuid(),
    market_id uuid references public.markets(id) on delete cascade,
    market_question text not null,
    side text not null check (side in ('YES', 'NO')),
    market_probability numeric not null check (market_probability >= 0 and market_probability <= 1),
    atris_probability numeric not null check (atris_probability >= 0 and atris_probability <= 1),
    edge numeric not null,
    confidence numeric not null check (confidence >= 0 and confidence <= 1),
    reasoning text not null,
    evidence_summary text not null,
    status text not null default 'active' check (status in ('active', 'resolved', 'expired')),
    result text not null default 'pending' check (result in ('correct', 'incorrect', 'pending')),
    created_at timestamptz not null default now(),
    resolved_at timestamptz
);

create table if not exists public.recommendation_evidence (
    id uuid primary key default gen_random_uuid(),
    recommendation_id uuid not null references public.recommendations(id) on delete cascade,
    source_url text not null,
    summary text not null,
    retrieved_at timestamptz not null default now()
);

create table if not exists public.agent_runs (
    id uuid primary key default gen_random_uuid(),
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    markets_scanned integer not null default 0,
    candidates_evaluated integer not null default 0,
    recommendations_published integer not null default 0,
    errors jsonb default '[]'::jsonb,
    status text not null check (status in ('success', 'partial', 'failed'))
);

create table if not exists public.performance_snapshots (
    id uuid primary key default gen_random_uuid(),
    snapshot_at timestamptz not null default now(),
    total_predictions integer not null default 0,
    correct integer not null default 0,
    incorrect integer not null default 0,
    pending integer not null default 0,
    accuracy_rate numeric not null default 0,
    average_edge numeric not null default 0
);

create unique index if not exists recommendations_one_active_side_per_market
    on public.recommendations (market_id, side)
    where status = 'active';

create index if not exists recommendations_status_created_at_idx
    on public.recommendations (status, created_at desc);

create index if not exists idx_recommendation_evidence_rec_id
    on public.recommendation_evidence (recommendation_id);

create index if not exists agent_runs_started_at_idx
    on public.agent_runs (started_at desc);

create index if not exists idx_performance_snapshots_snapshot_at
    on public.performance_snapshots (snapshot_at desc);

alter table public.markets enable row level security;
alter table public.recommendations enable row level security;
alter table public.recommendation_evidence enable row level security;
alter table public.agent_runs enable row level security;
alter table public.performance_snapshots enable row level security;
