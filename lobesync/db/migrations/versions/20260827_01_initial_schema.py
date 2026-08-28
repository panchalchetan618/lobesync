"""Create the initial Lobesync schema and upgrade the pre-migration schema."""

import sqlalchemy as sa
from sqlmodel import SQLModel

import lobesync.db.models  # noqa: F401
from alembic import op

revision = "20260827_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    application_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if not application_tables:
        SQLModel.metadata.create_all(bind)
        return

    columns = {column["name"] for column in inspector.get_columns("chat_sessions")}
    if "summary_message_count" not in columns:
        op.add_column(
            "chat_sessions",
            sa.Column("summary_message_count", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    raise RuntimeError("The initial Lobesync schema migration cannot be downgraded safely.")
