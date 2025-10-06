"""Load DeFiLlama yield pool data into PostgreSQL."""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional

import requests
from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://defillama:defillama@localhost:5432/defillama"
DEFAULT_SOURCE_URL = "https://yields.llama.fi/pools"

METADATA = MetaData()

CHAINS = Table(
    "chains",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
)

PROJECTS = Table(
    "projects",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
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
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)

POOL_SNAPSHOTS = Table(
    "pool_snapshots",
    METADATA,
    Column("id", Integer, primary_key=True),
    Column("pool_id", String, nullable=False),
    Column("snapshot_date", Date, nullable=False),
    Column("fetched_at", DateTime(timezone=True)),
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
    Column("created_at", DateTime(timezone=True)),
)


def get_engine() -> Engine:
    database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    return create_engine(database_url, future=True)


def wait_for_database(engine: Engine, retries: int = 10, delay: int = 3) -> None:
    """Block until the database is ready to accept connections."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(select(func.now()))
            LOGGER.info("Database connection established")
            return
        except OperationalError:
            LOGGER.info(
                "Database not ready (attempt %s/%s), retrying in %s seconds",
                attempt,
                retries,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError("Database is unavailable after multiple attempts")


def fetch_pools(source_url: str) -> List[Dict[str, Any]]:
    LOGGER.info("Fetching data from %s", source_url)
    response = requests.get(source_url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("Unexpected payload structure: missing 'data' list")
    LOGGER.info("Fetched %s pool records", len(data))
    return data


def to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def upsert_chain(connection, chain_name: str) -> int:
    statement = pg_insert(CHAINS).values(name=chain_name)
    statement = statement.on_conflict_do_update(
        index_elements=[CHAINS.c.name],
        set_={"name": statement.excluded.name},
    ).returning(CHAINS.c.id)
    return connection.execute(statement).scalar_one()


def upsert_project(connection, project_name: str) -> int:
    statement = pg_insert(PROJECTS).values(name=project_name)
    statement = statement.on_conflict_do_update(
        index_elements=[PROJECTS.c.name],
        set_={"name": statement.excluded.name},
    ).returning(PROJECTS.c.id)
    return connection.execute(statement).scalar_one()


def upsert_pool(connection, pool_id: str, chain_id: int, project_id: int, record: Dict[str, Any]) -> None:
    statement = (
        pg_insert(POOLS)
        .values(
            pool_id=pool_id,
            chain_id=chain_id,
            project_id=project_id,
            symbol=record.get("symbol"),
            stablecoin=record.get("stablecoin"),
            il_risk=record.get("ilRisk"),
            exposure=record.get("exposure"),
            reward_tokens=record.get("rewardTokens"),
            underlying_tokens=record.get("underlyingTokens"),
            pool_meta=record.get("poolMeta"),
            updated_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_update(
            index_elements=[POOLS.c.pool_id],
            set_={
                "chain_id": chain_id,
                "project_id": project_id,
                "symbol": record.get("symbol"),
                "stablecoin": record.get("stablecoin"),
                "il_risk": record.get("ilRisk"),
                "exposure": record.get("exposure"),
                "reward_tokens": record.get("rewardTokens"),
                "underlying_tokens": record.get("underlyingTokens"),
                "pool_meta": record.get("poolMeta"),
                "updated_at": func.now(),
            },
        )
    )
    connection.execute(statement)


def upsert_snapshot(
    connection,
    pool_id: str,
    record: Dict[str, Any],
    snapshot_date: date,
    fetched_at: datetime,
) -> None:
    predictions = record.get("predictions") or {}
    statement = (
        pg_insert(POOL_SNAPSHOTS)
        .values(
            pool_id=pool_id,
            snapshot_date=snapshot_date,
            fetched_at=fetched_at,
            tvl_usd=to_decimal(record.get("tvlUsd")),
            apy_base=to_decimal(record.get("apyBase")),
            apy_reward=to_decimal(record.get("apyReward")),
            apy=to_decimal(record.get("apy")),
            apy_pct_1d=to_decimal(record.get("apyPct1D")),
            apy_pct_7d=to_decimal(record.get("apyPct7D")),
            apy_pct_30d=to_decimal(record.get("apyPct30D")),
            il_7d=to_decimal(record.get("il7d")),
            apy_base_7d=to_decimal(record.get("apyBase7d")),
            apy_mean_30d=to_decimal(record.get("apyMean30d")),
            volume_usd_1d=to_decimal(record.get("volumeUsd1d")),
            volume_usd_7d=to_decimal(record.get("volumeUsd7d")),
            apy_base_inception=to_decimal(record.get("apyBaseInception")),
            mu=to_decimal(record.get("mu")),
            sigma=to_decimal(record.get("sigma")),
            observation_count=record.get("count"),
            outlier=record.get("outlier"),
            predicted_class=predictions.get("predictedClass"),
            predicted_probability=to_decimal(predictions.get("predictedProbability")),
            predicted_confidence_bin=predictions.get("binnedConfidence"),
            predictions=predictions if predictions else None,
            created_at=fetched_at,
        )
        .on_conflict_do_update(
            index_elements=[POOL_SNAPSHOTS.c.pool_id, POOL_SNAPSHOTS.c.snapshot_date],
            set_={
                "fetched_at": fetched_at,
                "tvl_usd": to_decimal(record.get("tvlUsd")),
                "apy_base": to_decimal(record.get("apyBase")),
                "apy_reward": to_decimal(record.get("apyReward")),
                "apy": to_decimal(record.get("apy")),
                "apy_pct_1d": to_decimal(record.get("apyPct1D")),
                "apy_pct_7d": to_decimal(record.get("apyPct7D")),
                "apy_pct_30d": to_decimal(record.get("apyPct30D")),
                "il_7d": to_decimal(record.get("il7d")),
                "apy_base_7d": to_decimal(record.get("apyBase7d")),
                "apy_mean_30d": to_decimal(record.get("apyMean30d")),
                "volume_usd_1d": to_decimal(record.get("volumeUsd1d")),
                "volume_usd_7d": to_decimal(record.get("volumeUsd7d")),
                "apy_base_inception": to_decimal(record.get("apyBaseInception")),
                "mu": to_decimal(record.get("mu")),
                "sigma": to_decimal(record.get("sigma")),
                "observation_count": record.get("count"),
                "outlier": record.get("outlier"),
                "predicted_class": predictions.get("predictedClass"),
                "predicted_probability": to_decimal(predictions.get("predictedProbability")),
                "predicted_confidence_bin": predictions.get("binnedConfidence"),
                "predictions": predictions if predictions else None,
            },
        )
    )
    connection.execute(statement)


def process_records(engine: Engine, records: Iterable[Dict[str, Any]]) -> int:
    snapshot_date = datetime.now(timezone.utc).date()
    fetched_at = datetime.now(timezone.utc)
    ingested = 0

    with engine.begin() as connection:
        for record in records:
            pool_id = record.get("pool")
            chain = record.get("chain")
            project = record.get("project")

            if not pool_id or not chain or not project:
                LOGGER.warning("Skipping record due to missing identifiers: %s", json.dumps(record)[:200])
                continue

            chain_id = upsert_chain(connection, chain)
            project_id = upsert_project(connection, project)
            upsert_pool(connection, pool_id, chain_id, project_id, record)
            upsert_snapshot(connection, pool_id, record, snapshot_date, fetched_at)
            ingested += 1

    return ingested


def main() -> None:
    engine = get_engine()
    wait_for_database(engine)

    source_url = os.getenv("SOURCE_URL", DEFAULT_SOURCE_URL)
    records = fetch_pools(source_url)
    ingested = process_records(engine, records)
    LOGGER.info("Successfully ingested %s records", ingested)


if __name__ == "__main__":
    main()
