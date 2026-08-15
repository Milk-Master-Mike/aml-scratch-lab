"""Create the Milestone 1 database foundation."""

from alembic import op
from apps.api.app import db_models  # noqa: F401
from apps.api.app.database import Base

revision = "0001_database_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
