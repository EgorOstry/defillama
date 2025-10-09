# DeFiLlama Yield Pool Ingestion

This project provisions a PostgreSQL database and a Python-based ingestion job that downloads yield pool data from [DeFiLlama](https://yields.llama.fi/pools) and stores it with a schema that supports daily snapshots and future dataset expansion. The job also enriches the `projects` dimension with protocol metadata from [https://api.llama.fi/protocols](https://api.llama.fi/protocols).

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose v2

## Getting started

1. Start the PostgreSQL database:
   ```bash
   docker compose up -d db
   ```

   The database is exposed on port `5432` with the following defaults:
   - database: `defillama`
   - user: `defillama`
   - password: `defillama`

2. Apply database migrations (run this before each ingestion to pick up schema changes):
   ```bash
   docker compose run --rm ingestion alembic upgrade head
   ```

   To roll back the most recent migration if needed:
   ```bash
   docker compose run --rm ingestion alembic downgrade -1
   ```

3. Run the ingestion job:
   ```bash
   docker compose run --rm ingestion
   ```

   The job waits for the database to become available, fetches the JSON payload from `https://yields.llama.fi/pools`, and upserts the data into the schema managed through Alembic migrations in [`ingestion/migrations`](ingestion/migrations).

4. Inspect the data using any PostgreSQL client. For example, with `psql`:
   ```bash
   docker compose exec db psql -U defillama -d defillama
   select count(*) from pool_snapshots;
   ```

## Schema overview

- **chains**: master table of blockchain networks referenced by pools.
- **projects**: master table of DeFi projects/protocols populated from the `https://api.llama.fi/protocols` endpoint. Stores identifiers (name, slug, symbol), categorical attributes (category, chains, audits), descriptive metadata, and aggregated TVL and market metrics used for analytics.
- **pools**: metadata for each pool, keyed by the `pool` identifier from DeFiLlama. Stores exposure, risk, and token metadata.
- **pool_snapshots**: daily snapshot metrics for each pool, enabling time-series queries and incremental refreshes.

The schema is designed for repeated daily loads and for future integration of other DeFiLlama datasets that share chain/project dimensions.

## Configuration

Environment variables can override defaults:

- `DATABASE_URL`: PostgreSQL connection string (defaults to `postgresql://defillama:defillama@db:5432/defillama` inside Docker).
- `SOURCE_URL`: API endpoint for pool snapshots (defaults to `https://yields.llama.fi/pools`).
- `PROTOCOLS_URL`: API endpoint for protocol metadata (defaults to `https://api.llama.fi/protocols`).

You can also create a `.env` file alongside the ingestion script to supply these variables locally.

## Development notes

- To run the ingester locally without Docker, install dependencies from [`ingestion/requirements.txt`](ingestion/requirements.txt) and execute `alembic -c ingestion/alembic.ini upgrade head` followed by `python ingestion/ingest.py`.
- The ingestion job uses upsert logic so repeated executions will update existing rows for the same day rather than creating duplicates.
