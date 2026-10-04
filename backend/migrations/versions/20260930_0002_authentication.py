"""Add authentication fields to users."""

from alembic import op
import sqlalchemy as sa

revision = "20260930_0002"
down_revision = "20260930_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), server_default="owner", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")
