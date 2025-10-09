"""Initial schema."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240524_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chains",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("slug", sa.String(), unique=True),
        sa.Column("symbol", sa.String()),
        sa.Column("chain", sa.String()),
        sa.Column("chains", postgresql.ARRAY(sa.String())),
        sa.Column("category", sa.String()),
        sa.Column("description", sa.Text()),
        sa.Column("twitter", sa.String()),
        sa.Column("listed_at", sa.DateTime(timezone=True)),
        sa.Column("tvl", sa.Numeric()),
        sa.Column("tvl_prev_day", sa.Numeric()),
        sa.Column("tvl_prev_week", sa.Numeric()),
        sa.Column("tvl_prev_month", sa.Numeric()),
        sa.Column("mcap", sa.Numeric()),
        sa.Column("fdv", sa.Numeric()),
        sa.Column("change_1h", sa.Numeric()),
        sa.Column("change_1d", sa.Numeric()),
        sa.Column("change_7d", sa.Numeric()),
        sa.Column("chain_tvls", postgresql.JSONB()),
        sa.Column("tokens", postgresql.JSONB()),
        sa.Column("audits", sa.String()),
        sa.Column("audit_note", sa.Text()),
        sa.Column("forked_from", postgresql.ARRAY(sa.String())),
        sa.Column("oracles", postgresql.ARRAY(sa.String())),
        sa.Column("parent_protocols", postgresql.ARRAY(sa.String())),
        sa.Column("other_chains", postgresql.ARRAY(sa.String())),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint("uq_projects_slug", "projects", ["slug"])

    op.create_table(
        "pools",
        sa.Column("pool_id", sa.String(), primary_key=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String()),
        sa.Column("stablecoin", sa.Boolean()),
        sa.Column("il_risk", sa.String()),
        sa.Column("exposure", sa.String()),
        sa.Column("reward_tokens", postgresql.ARRAY(sa.String())),
        sa.Column("underlying_tokens", postgresql.ARRAY(sa.String())),
        sa.Column("pool_meta", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["chain_id"], ["chains.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
    )
    op.create_index("idx_pools_chain_id", "pools", ["chain_id"])
    op.create_index("idx_pools_project_id", "pools", ["project_id"])

    op.create_table(
        "pool_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("pool_id", sa.String(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("tvl_usd", sa.Numeric()),
        sa.Column("apy_base", sa.Numeric()),
        sa.Column("apy_reward", sa.Numeric()),
        sa.Column("apy", sa.Numeric()),
        sa.Column("apy_pct_1d", sa.Numeric()),
        sa.Column("apy_pct_7d", sa.Numeric()),
        sa.Column("apy_pct_30d", sa.Numeric()),
        sa.Column("il_7d", sa.Numeric()),
        sa.Column("apy_base_7d", sa.Numeric()),
        sa.Column("apy_mean_30d", sa.Numeric()),
        sa.Column("volume_usd_1d", sa.Numeric()),
        sa.Column("volume_usd_7d", sa.Numeric()),
        sa.Column("apy_base_inception", sa.Numeric()),
        sa.Column("mu", sa.Numeric()),
        sa.Column("sigma", sa.Numeric()),
        sa.Column("observation_count", sa.Integer()),
        sa.Column("outlier", sa.Boolean()),
        sa.Column("predicted_class", sa.String()),
        sa.Column("predicted_probability", sa.Numeric()),
        sa.Column("predicted_confidence_bin", sa.Integer()),
        sa.Column("predictions", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.pool_id"], ondelete="CASCADE"),
    )
    op.create_unique_constraint(
        "uq_pool_snapshots_pool_id_snapshot_date",
        "pool_snapshots",
        ["pool_id", "snapshot_date"],
    )
    op.create_index("idx_pool_snapshots_pool_date", "pool_snapshots", ["pool_id", "snapshot_date"])


def downgrade() -> None:
    op.drop_index("idx_pool_snapshots_pool_date", table_name="pool_snapshots")
    op.drop_constraint("uq_pool_snapshots_pool_id_snapshot_date", "pool_snapshots", type_="unique")
    op.drop_table("pool_snapshots")

    op.drop_index("idx_pools_project_id", table_name="pools")
    op.drop_index("idx_pools_chain_id", table_name="pools")
    op.drop_table("pools")

    op.drop_constraint("uq_projects_slug", "projects", type_="unique")
    op.drop_table("projects")

    op.drop_table("chains")
