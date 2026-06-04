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

create table if not exists public.f1_sources (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    kind text not null check (kind in ('historical', 'live', 'analysis', 'market')),
    status text not null check (status in ('ready', 'evaluating', 'roadmap')),
    access text not null,
    role text not null,
    notes text not null,
    url text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.f1_ingestion_runs (
    id uuid primary key default gen_random_uuid(),
    source_name text not null,
    ingestion_type text not null,
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    status text not null check (status in ('success', 'partial', 'failed')),
    records_processed integer not null default 0,
    errors jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.f1_races (
    id uuid primary key default gen_random_uuid(),
    season integer not null,
    round integer not null,
    race_name text not null,
    circuit_name text not null,
    locality text,
    country text,
    race_date date,
    race_time text,
    source_name text not null default 'Jolpica-F1',
    source_payload jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (season, round)
);

create table if not exists public.f1_sessions (
    id uuid primary key default gen_random_uuid(),
    session_key integer not null unique,
    meeting_key integer not null,
    year integer not null,
    session_name text not null,
    session_type text not null,
    country_name text,
    location text,
    circuit_short_name text,
    date_start timestamptz,
    date_end timestamptz,
    source_name text not null default 'OpenF1',
    source_payload jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.f1_race_results (
    id uuid primary key default gen_random_uuid(),
    season integer not null,
    round integer not null,
    race_name text,
    driver_id text not null,
    driver_code text,
    driver_number text,
    given_name text,
    family_name text,
    constructor_id text,
    constructor_name text,
    grid integer,
    position integer,
    position_text text,
    position_order integer,
    points numeric not null default 0,
    laps integer,
    status text,
    race_time text,
    fastest_lap_rank integer,
    fastest_lap_time text,
    source_name text not null default 'Jolpica-F1',
    source_payload jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (season, round, driver_id)
);

create table if not exists public.f1_qualifying_results (
    id uuid primary key default gen_random_uuid(),
    season integer not null,
    round integer not null,
    race_name text,
    driver_id text not null,
    driver_code text,
    driver_number text,
    given_name text,
    family_name text,
    constructor_id text,
    constructor_name text,
    qualifying_position integer,
    q1 text,
    q2 text,
    q3 text,
    source_name text not null default 'Jolpica-F1',
    source_payload jsonb not null default '{}'::jsonb,
    fetched_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (season, round, driver_id)
);

create table if not exists public.f1_driver_season_features (
    id uuid primary key default gen_random_uuid(),
    season integer not null,
    driver_id text not null,
    driver_code text,
    driver_number text,
    given_name text,
    family_name text,
    constructor_id text,
    constructor_name text,
    starts integer not null default 0,
    qualifying_sessions integer not null default 0,
    points numeric not null default 0,
    wins integer not null default 0,
    podiums integer not null default 0,
    points_finishes integer not null default 0,
    dnfs integer not null default 0,
    poles integer not null default 0,
    q3_appearances integer not null default 0,
    avg_finish_position numeric,
    avg_grid_position numeric,
    avg_qualifying_position numeric,
    points_per_start numeric,
    podium_rate numeric,
    points_finish_rate numeric,
    dnf_rate numeric,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (season, driver_id)
);

create table if not exists public.f1_constructor_season_features (
    id uuid primary key default gen_random_uuid(),
    season integer not null,
    constructor_id text not null,
    constructor_name text,
    starts integer not null default 0,
    driver_count integer not null default 0,
    points numeric not null default 0,
    wins integer not null default 0,
    podiums integer not null default 0,
    points_finishes integer not null default 0,
    dnfs integer not null default 0,
    poles integer not null default 0,
    q3_appearances integer not null default 0,
    avg_finish_position numeric,
    avg_grid_position numeric,
    avg_qualifying_position numeric,
    points_per_start numeric,
    podium_rate numeric,
    points_finish_rate numeric,
    dnf_rate numeric,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (season, constructor_id)
);

create table if not exists public.f1_model_training_examples (
    id uuid primary key default gen_random_uuid(),
    season integer not null,
    round integer not null,
    race_name text,
    driver_id text not null,
    driver_code text,
    constructor_id text,
    constructor_name text,
    outcome_type text not null check (outcome_type in ('points_finish', 'podium_finish')),
    label boolean not null,
    feature_set text not null default 'pre_race_v1',
    features jsonb not null,
    source_result jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (season, round, driver_id, outcome_type, feature_set)
);

create table if not exists public.f1_market_links (
    id uuid primary key default gen_random_uuid(),
    market_id uuid references public.markets(id) on delete cascade,
    polymarket_id text,
    domain text not null default 'f1',
    entity_type text,
    entity_key text,
    outcome_type text,
    confidence numeric not null default 0 check (confidence >= 0 and confidence <= 1),
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.f1_feature_snapshots (
    id uuid primary key default gen_random_uuid(),
    market_id uuid references public.markets(id) on delete cascade,
    session_key integer references public.f1_sessions(session_key) on delete set null,
    feature_set text not null,
    features jsonb not null,
    source_freshness jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.f1_model_versions (
    id uuid primary key default gen_random_uuid(),
    model_name text not null,
    outcome_type text not null,
    version text not null,
    status text not null default 'candidate' check (status in ('candidate', 'active', 'retired')),
    training_window jsonb not null default '{}'::jsonb,
    feature_schema jsonb not null default '{}'::jsonb,
    metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (model_name, version)
);

create table if not exists public.f1_model_predictions (
    id uuid primary key default gen_random_uuid(),
    model_version_id uuid references public.f1_model_versions(id) on delete set null,
    market_id uuid references public.markets(id) on delete cascade,
    feature_snapshot_id uuid references public.f1_feature_snapshots(id) on delete set null,
    outcome_type text not null,
    subject text not null,
    probability numeric not null check (probability >= 0 and probability <= 1),
    confidence numeric not null default 0 check (confidence >= 0 and confidence <= 1),
    prediction_mode text not null check (prediction_mode in ('pre_race', 'race_weekend', 'live_race')),
    explanation jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists public.f1_model_backtest_predictions (
    id uuid primary key default gen_random_uuid(),
    model_version_id uuid references public.f1_model_versions(id) on delete cascade,
    season integer not null,
    round integer not null,
    race_name text,
    driver_id text not null,
    driver_code text,
    constructor_id text,
    outcome_type text not null check (outcome_type in ('points_finish', 'podium_finish')),
    label boolean not null,
    probability numeric not null check (probability >= 0 and probability <= 1),
    predicted_label boolean not null,
    feature_set text not null,
    split text not null check (split in ('train', 'eval')),
    features jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (model_version_id, season, round, driver_id, outcome_type, feature_set)
);

create table if not exists public.f1_market_edge_snapshots (
    id uuid primary key default gen_random_uuid(),
    prediction_id uuid references public.f1_model_predictions(id) on delete cascade,
    market_id uuid references public.markets(id) on delete cascade,
    polymarket_id text,
    model_probability numeric not null check (model_probability >= 0 and model_probability <= 1),
    market_probability numeric not null check (market_probability >= 0 and market_probability <= 1),
    edge numeric not null,
    liquidity numeric,
    volume numeric,
    spread numeric,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists f1_ingestion_runs_started_at_idx
    on public.f1_ingestion_runs (started_at desc);

create index if not exists f1_races_season_date_idx
    on public.f1_races (season, race_date);

create index if not exists f1_sessions_year_type_idx
    on public.f1_sessions (year, session_type, date_start);

create index if not exists f1_race_results_season_round_idx
    on public.f1_race_results (season, round, position_order);

create index if not exists f1_race_results_driver_idx
    on public.f1_race_results (driver_id, season);

create index if not exists f1_qualifying_results_season_round_idx
    on public.f1_qualifying_results (season, round, qualifying_position);

create index if not exists f1_qualifying_results_driver_idx
    on public.f1_qualifying_results (driver_id, season);

create index if not exists f1_driver_season_features_points_idx
    on public.f1_driver_season_features (season, points desc);

create index if not exists f1_constructor_season_features_points_idx
    on public.f1_constructor_season_features (season, points desc);

create index if not exists f1_model_training_examples_season_outcome_idx
    on public.f1_model_training_examples (season, outcome_type);

create index if not exists f1_model_training_examples_driver_idx
    on public.f1_model_training_examples (driver_id, season);

create index if not exists f1_market_links_polymarket_id_idx
    on public.f1_market_links (polymarket_id);

create index if not exists f1_market_links_market_id_idx
    on public.f1_market_links (market_id);

create index if not exists f1_feature_snapshots_market_created_idx
    on public.f1_feature_snapshots (market_id, created_at desc);

create index if not exists f1_feature_snapshots_session_key_idx
    on public.f1_feature_snapshots (session_key);

create index if not exists f1_model_predictions_market_created_idx
    on public.f1_model_predictions (market_id, created_at desc);

create index if not exists f1_model_predictions_model_version_id_idx
    on public.f1_model_predictions (model_version_id);

create index if not exists f1_model_predictions_feature_snapshot_id_idx
    on public.f1_model_predictions (feature_snapshot_id);

create index if not exists f1_model_backtest_predictions_model_idx
    on public.f1_model_backtest_predictions (model_version_id);

create index if not exists f1_model_backtest_predictions_season_outcome_idx
    on public.f1_model_backtest_predictions (season, outcome_type, round);

create index if not exists f1_market_edge_snapshots_market_created_idx
    on public.f1_market_edge_snapshots (market_id, created_at desc);

create index if not exists f1_market_edge_snapshots_prediction_id_idx
    on public.f1_market_edge_snapshots (prediction_id);

alter table public.markets enable row level security;
alter table public.recommendations enable row level security;
alter table public.recommendation_evidence enable row level security;
alter table public.agent_runs enable row level security;
alter table public.performance_snapshots enable row level security;
alter table public.f1_sources enable row level security;
alter table public.f1_ingestion_runs enable row level security;
alter table public.f1_races enable row level security;
alter table public.f1_sessions enable row level security;
alter table public.f1_race_results enable row level security;
alter table public.f1_qualifying_results enable row level security;
alter table public.f1_driver_season_features enable row level security;
alter table public.f1_constructor_season_features enable row level security;
alter table public.f1_model_training_examples enable row level security;
alter table public.f1_market_links enable row level security;
alter table public.f1_feature_snapshots enable row level security;
alter table public.f1_model_versions enable row level security;
alter table public.f1_model_predictions enable row level security;
alter table public.f1_model_backtest_predictions enable row level security;
alter table public.f1_market_edge_snapshots enable row level security;
