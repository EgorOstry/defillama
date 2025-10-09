CREATE TABLE IF NOT EXISTS chains (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    slug TEXT UNIQUE,
    symbol TEXT,
    chain TEXT,
    chains TEXT[],
    category TEXT,
    description TEXT,
    twitter TEXT,
    listed_at TIMESTAMPTZ,
    tvl NUMERIC,
    tvl_prev_day NUMERIC,
    tvl_prev_week NUMERIC,
    tvl_prev_month NUMERIC,
    mcap NUMERIC,
    fdv NUMERIC,
    change_1h NUMERIC,
    change_1d NUMERIC,
    change_7d NUMERIC,
    chain_tvls JSONB,
    tokens JSONB,
    audits TEXT,
    audit_note TEXT,
    forked_from TEXT[],
    oracles TEXT[],
    parent_protocols TEXT[],
    other_chains TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE projects ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS symbol TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS chain TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS chains TEXT[];
ALTER TABLE projects ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS twitter TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS listed_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tvl NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tvl_prev_day NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tvl_prev_week NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tvl_prev_month NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS mcap NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS fdv NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS change_1h NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS change_1d NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS change_7d NUMERIC;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS chain_tvls JSONB;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tokens JSONB;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS audits TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS audit_note TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS forked_from TEXT[];
ALTER TABLE projects ADD COLUMN IF NOT EXISTS oracles TEXT[];
ALTER TABLE projects ADD COLUMN IF NOT EXISTS parent_protocols TEXT[];
ALTER TABLE projects ADD COLUMN IF NOT EXISTS other_chains TEXT[];
ALTER TABLE projects ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
ALTER TABLE projects ALTER COLUMN updated_at SET DEFAULT NOW();
UPDATE projects SET updated_at = NOW() WHERE updated_at IS NULL;
ALTER TABLE projects ALTER COLUMN updated_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);

CREATE TABLE IF NOT EXISTS pools (
    pool_id TEXT PRIMARY KEY,
    chain_id INTEGER NOT NULL REFERENCES chains(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    symbol TEXT,
    stablecoin BOOLEAN,
    il_risk TEXT,
    exposure TEXT,
    reward_tokens TEXT[],
    underlying_tokens TEXT[],
    pool_meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pools_chain_id ON pools(chain_id);
CREATE INDEX IF NOT EXISTS idx_pools_project_id ON pools(project_id);

CREATE TABLE IF NOT EXISTS pool_snapshots (
    id BIGSERIAL PRIMARY KEY,
    pool_id TEXT NOT NULL REFERENCES pools(pool_id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tvl_usd NUMERIC,
    apy_base NUMERIC,
    apy_reward NUMERIC,
    apy NUMERIC,
    apy_pct_1d NUMERIC,
    apy_pct_7d NUMERIC,
    apy_pct_30d NUMERIC,
    il_7d NUMERIC,
    apy_base_7d NUMERIC,
    apy_mean_30d NUMERIC,
    volume_usd_1d NUMERIC,
    volume_usd_7d NUMERIC,
    apy_base_inception NUMERIC,
    mu NUMERIC,
    sigma NUMERIC,
    observation_count INTEGER,
    outlier BOOLEAN,
    predicted_class TEXT,
    predicted_probability NUMERIC,
    predicted_confidence_bin INTEGER,
    predictions JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pool_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_pool_snapshots_pool_date ON pool_snapshots(pool_id, snapshot_date DESC);
