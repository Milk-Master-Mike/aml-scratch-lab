"""Add Milestone 3 enrichment jobs and evidence findings."""

import sqlalchemy as sa

from alembic import op

revision = "0003_enrichment"
down_revision = "0002_testing_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "enrichment_jobs" not in tables:
        op.create_table(
            "enrichment_jobs",
            sa.Column("job_id", sa.String(36), primary_key=True),
            sa.Column("alert_id", sa.String(36), sa.ForeignKey("alerts.alert_id"), unique=True),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
        )
    if "enrichment_sources" not in tables:
        op.create_table(
            "enrichment_sources",
            sa.Column("execution_id", sa.String(36), primary_key=True),
            sa.Column(
                "job_id", sa.String(36), sa.ForeignKey("enrichment_jobs.job_id"), nullable=False
            ),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("provenance", sa.JSON(), nullable=False),
            sa.Column("error", sa.Text()),
        )
    if "evidence_findings" not in tables:
        op.create_table(
            "evidence_findings",
            sa.Column("finding_id", sa.String(36), primary_key=True),
            sa.Column(
                "execution_id",
                sa.String(36),
                sa.ForeignKey("enrichment_sources.execution_id"),
                nullable=False,
            ),
            sa.Column("finding_type", sa.String(32), nullable=False),
            sa.Column("outcome", sa.String(32), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("score", sa.Numeric(5, 4)),
            sa.Column("source_record_id", sa.String(120)),
            sa.Column("details", sa.JSON(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("evidence_findings")
    op.drop_table("enrichment_sources")
    op.drop_table("enrichment_jobs")
