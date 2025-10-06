CREATE TABLE IF NOT EXISTS chains (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
