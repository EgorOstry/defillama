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
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError

from schema import (
    CHAINS,
    DEFAULT_DATABASE_URL,
    METADATA,
    POOLS,
    POOL_SNAPSHOTS,
    PROJECTS,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)

DEFAULT_SOURCE_URL = "https://yields.llama.fi/pools"
DEFAULT_PROTOCOLS_URL = "https://api.llama.fi/protocols"


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


def fetch_protocols(source_url: str) -> List[Dict[str, Any]]:
    LOGGER.info("Fetching protocol metadata from %s", source_url)
    response = requests.get(source_url, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected protocol payload structure: expected a list")
    LOGGER.info("Fetched %s protocol records", len(data))
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


def to_utc_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (ValueError, TypeError, OSError, OverflowError):
        return None


def to_text_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        items = [value]
    else:
        try:
            items = list(value)
        except TypeError:
            return None
    normalized = [str(item) for item in items if item not in (None, "")]
    return normalized or None


def sanitize_json(value: Any) -> Any:
    if value in (None, {}, []):
        return None
    return value


def upsert_chain(connection, chain_name: str) -> int:
    statement = pg_insert(CHAINS).values(name=chain_name)
    statement = statement.on_conflict_do_update(
        index_elements=[CHAINS.c.name],
        set_={"name": statement.excluded.name},
    ).returning(CHAINS.c.id)
    return connection.execute(statement).scalar_one()


def ensure_project(connection, project_name: str) -> int:
    insert_stmt = pg_insert(PROJECTS).values(
        name=project_name,
        updated_at=datetime.now(timezone.utc),
    )
    statement = insert_stmt.on_conflict_do_update(
        index_elements=[PROJECTS.c.name],
        set_={"name": insert_stmt.excluded.name, "updated_at": func.now()},
    ).returning(PROJECTS.c.id)
    return connection.execute(statement).scalar_one()


def upsert_project_metadata(connection, record: Dict[str, Any]) -> Optional[int]:
    name = record.get("name")
    if not name:
        return None

    audits = record.get("audits")
    audit_note = record.get("audit_note")

    values: Dict[str, Any] = {
        "name": name,
        "slug": record.get("slug"),
        "symbol": record.get("symbol"),
        "chain": record.get("chain"),
        "chains": to_text_list(record.get("chains")),
        "category": record.get("category"),
        "description": record.get("description"),
        "twitter": record.get("twitter"),
        "listed_at": to_utc_datetime(record.get("listedAt")),
        "tvl": to_decimal(record.get("tvl")),
        "tvl_prev_day": to_decimal(record.get("tvlPrevDay")),
        "tvl_prev_week": to_decimal(record.get("tvlPrevWeek")),
        "tvl_prev_month": to_decimal(record.get("tvlPrevMonth")),
        "mcap": to_decimal(record.get("mcap")),
        "fdv": to_decimal(record.get("fdv")),
        "change_1h": to_decimal(record.get("change_1h")),
        "change_1d": to_decimal(record.get("change_1d")),
        "change_7d": to_decimal(record.get("change_7d")),
        "chain_tvls": sanitize_json(record.get("chainTvls")),
        "tokens": sanitize_json(record.get("tokens")),
        "audits": str(audits) if audits not in (None, "") else None,
        "audit_note": audit_note if audit_note not in (None, "") else None,
        "forked_from": to_text_list(record.get("forkedFrom")),
        "oracles": to_text_list(record.get("oracles")),
        "parent_protocols": to_text_list(record.get("parentProtocol")),
        "other_chains": to_text_list(record.get("otherChains")),
        "updated_at": datetime.now(timezone.utc),
    }

    insert_stmt = pg_insert(PROJECTS).values(**values)
    update_values = values.copy()
    update_values.pop("name", None)
    update_values["updated_at"] = func.now()

    statement = insert_stmt.on_conflict_do_update(
        index_elements=[PROJECTS.c.name],
        set_=update_values,
    ).returning(PROJECTS.c.id)

    return connection.execute(statement).scalar_one()


def sync_projects(engine: Engine, protocols: Iterable[Dict[str, Any]]) -> int:
    if not protocols:
        return 0

    upserted = 0
    with engine.begin() as connection:
        for record in protocols:
            if not isinstance(record, dict):
                continue
            result = upsert_project_metadata(connection, record)
            if result is not None:
                upserted += 1

    LOGGER.info("Upserted %s protocol metadata records", upserted)
    return upserted


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
            project_id = ensure_project(connection, project)
            upsert_pool(connection, pool_id, chain_id, project_id, record)
            upsert_snapshot(connection, pool_id, record, snapshot_date, fetched_at)
            ingested += 1

    return ingested


def main() -> None:
    engine = get_engine()
    wait_for_database(engine)

    protocols_url = os.getenv("PROTOCOLS_URL", DEFAULT_PROTOCOLS_URL)
    protocol_records = fetch_protocols(protocols_url)
    sync_projects(engine, protocol_records)

    source_url = os.getenv("SOURCE_URL", DEFAULT_SOURCE_URL)
    records = fetch_pools(source_url)
    ingested = process_records(engine, records)
    LOGGER.info("Successfully ingested %s records", ingested)


if __name__ == "__main__":
    main()
