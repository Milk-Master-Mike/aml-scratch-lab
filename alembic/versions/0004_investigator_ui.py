"""Add Milestone 4 investigation cases and analyst notes."""

import uuid
from datetime import timezone

import sqlalchemy as sa

from alembic import op

revision = "0004_investigator_ui"
down_revision = "0003_enrichment"
branch_labels = None
depends_on = None


def _case_number(executed_at, case_id: str) -> str:
    if executed_at.tzinfo is None:
        executed_at = executed_at.replace(tzinfo=timezone.utc)
    return f"AML-{executed_at.year}-{case_id[:8].upper()}"


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "cases" not in tables:
        op.create_table(
            "cases",
            sa.Column("case_id", sa.String(36), primary_key=True),
            sa.Column("case_number", sa.String(32), nullable=False, unique=True),
            sa.Column("alert_id", sa.String(36), sa.ForeignKey("alerts.alert_id"), nullable=False, unique=True),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        connection = op.get_bind()
        alert = sa.table("alerts", sa.column("alert_id"), sa.column("run_id"))
        test_run = sa.table("test_runs", sa.column("run_id"), sa.column("executed_at"))
        case = sa.table(
            "cases",
            sa.column("case_id"), sa.column("case_number"), sa.column("alert_id"),
            sa.column("status"), sa.column("created_at"), sa.column("updated_at"),
        )
        rows = connection.execute(
            sa.select(alert.c.alert_id, test_run.c.executed_at).join(
                test_run, alert.c.run_id == test_run.c.run_id
            )
        )
        for row in rows:
            case_id = str(uuid.uuid4())
            connection.execute(case.insert().values(
                case_id=case_id,
                case_number=_case_number(row.executed_at, case_id),
                alert_id=row.alert_id,
                status="open",
                created_at=row.executed_at,
                updated_at=row.executed_at,
            ))
    if "analyst_notes" not in tables:
        op.create_table(
            "analyst_notes",
            sa.Column("note_id", sa.String(36), primary_key=True),
            sa.Column("case_id", sa.String(36), sa.ForeignKey("cases.case_id"), nullable=False),
            sa.Column("author", sa.String(80), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("analyst_notes")
    op.drop_table("cases")
