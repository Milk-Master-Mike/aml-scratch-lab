"""Add Milestone 2 control versioning and regression batches."""

import sqlalchemy as sa

from alembic import op

revision = "0002_testing_platform"
down_revision = "0001_database_foundation"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "control_versions" not in tables:
        op.create_table(
            "control_versions",
            sa.Column("control_id", sa.String(32), primary_key=True),
            sa.Column("version", sa.Integer(), primary_key=True),
            sa.Column("fingerprint", sa.String(64), nullable=False),
            sa.Column("definition", sa.JSON(), nullable=False),
            sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "regression_batches" not in tables:
        op.create_table(
            "regression_batches",
            sa.Column("batch_id", sa.String(36), primary_key=True),
            sa.Column("seed", sa.Integer(), nullable=False),
            sa.Column("days", sa.Integer(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("total", sa.Integer(), nullable=False),
            sa.Column("passed", sa.Integer(), nullable=False),
            sa.Column("failed", sa.Integer(), nullable=False),
            sa.Column("untested", sa.Integer(), nullable=False),
            sa.Column("coverage", sa.Numeric(5, 2), nullable=False),
            sa.Column("mutation", sa.JSON()),
        )
    columns = _columns("test_runs")
    with op.batch_alter_table("test_runs") as batch:
        if "batch_id" not in columns:
            batch.add_column(sa.Column("batch_id", sa.String(36), nullable=True))
            batch.create_foreign_key(
                "fk_test_runs_batch", "regression_batches", ["batch_id"], ["batch_id"]
            )
        if "failure_reason" not in columns:
            batch.add_column(sa.Column("failure_reason", sa.Text(), nullable=True))
        batch.alter_column("actual_alert", existing_type=sa.Boolean(), nullable=True)


def downgrade() -> None:
    columns = _columns("test_runs")
    with op.batch_alter_table("test_runs") as batch:
        if "failure_reason" in columns:
            batch.drop_column("failure_reason")
        if "batch_id" in columns:
            batch.drop_column("batch_id")
        batch.alter_column("actual_alert", existing_type=sa.Boolean(), nullable=False)
    op.drop_table("regression_batches")
    op.drop_table("control_versions")
