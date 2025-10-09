"""Shared database schema definitions for ingestion and migrations."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

DEFAULT_DATABASE_URL = "postgresql://defillama:defillama@localhost:5432/defillama"

METADATA = MetaData()

CHAINS = Table(
    "chains",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

PROJECTS = Table(
    "projects",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("slug", String, unique=True),
    Column("symbol", String),
    Column("chain", String),
    Column("chains", ARRAY(String)),
    Column("category", String),
    Column("description", Text),
    Column("twitter", String),
    Column("listed_at", DateTime(timezone=True)),
    Column("tvl", Numeric),
    Column("tvl_prev_day", Numeric),
    Column("tvl_prev_week", Numeric),
    Column("tvl_prev_month", Numeric),
    Column("mcap", Numeric),
    Column("fdv", Numeric),
    Column("change_1h", Numeric),
    Column("change_1d", Numeric),
    Column("change_7d", Numeric),
    Column("chain_tvls", JSONB),
    Column("tokens", JSONB),
    Column("audits", String),
    Column("audit_note", Text),
    Column("forked_from", ARRAY(String)),
    Column("oracles", ARRAY(String)),
    Column("parent_protocols", ARRAY(String)),
    Column("other_chains", ARRAY(String)),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

POOLS = Table(
    "pools",
    METADATA,
    Column("pool_id", String, primary_key=True),
    Column("chain_id", Integer, nullable=False),
    Column("project_id", Integer, nullable=False),
    Column("symbol", String),
    Column("stablecoin", Boolean),
    Column("il_risk", String),
    Column("exposure", String),
    Column("reward_tokens", ARRAY(String)),
    Column("underlying_tokens", ARRAY(String)),
    Column("pool_meta", JSONB),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column(
        "updated_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

POOL_SNAPSHOTS = Table(
    "pool_snapshots",
    METADATA,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("pool_id", String, nullable=False),
    Column("snapshot_date", Date, nullable=False),
    Column(
        "fetched_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column("tvl_usd", Numeric),
    Column("apy_base", Numeric),
    Column("apy_reward", Numeric),
    Column("apy", Numeric),
    Column("apy_pct_1d", Numeric),
    Column("apy_pct_7d", Numeric),
    Column("apy_pct_30d", Numeric),
    Column("il_7d", Numeric),
    Column("apy_base_7d", Numeric),
    Column("apy_mean_30d", Numeric),
    Column("volume_usd_1d", Numeric),
    Column("volume_usd_7d", Numeric),
    Column("apy_base_inception", Numeric),
    Column("mu", Numeric),
    Column("sigma", Numeric),
    Column("observation_count", Integer),
    Column("outlier", Boolean),
    Column("predicted_class", String),
    Column("predicted_probability", Numeric),
    Column("predicted_confidence_bin", Integer),
    Column("predictions", JSONB),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
)

__all__ = [
    "DEFAULT_DATABASE_URL",
    "METADATA",
    "CHAINS",
    "PROJECTS",
    "POOLS",
    "POOL_SNAPSHOTS",
]
