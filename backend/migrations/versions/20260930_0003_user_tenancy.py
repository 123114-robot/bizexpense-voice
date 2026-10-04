"""Scope suppliers and documents to a user tenant."""

from alembic import op
import sqlalchemy as sa

revision = "20260930_0003"
down_revision = "20260930_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("suppliers") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_suppliers_user_id", "users", ["user_id"], ["id"])
    with op.batch_alter_table("uploaded_documents") as batch:
        batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_documents_user_id", "users", ["user_id"], ["id"])

    op.execute(
        "UPDATE suppliers SET user_id = COALESCE((SELECT MIN(user_id) FROM expenses WHERE expenses.supplier_id = suppliers.id), (SELECT MIN(id) FROM users))"
    )
    op.execute(
        "UPDATE uploaded_documents SET user_id = COALESCE((SELECT MIN(user_id) FROM expenses WHERE expenses.document_id = uploaded_documents.id), (SELECT MIN(id) FROM users))"
    )
    with op.batch_alter_table("suppliers") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("uploaded_documents") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("uploaded_documents") as batch:
        batch.drop_constraint("fk_documents_user_id", type_="foreignkey")
        batch.drop_column("user_id")
    with op.batch_alter_table("suppliers") as batch:
        batch.drop_constraint("fk_suppliers_user_id", type_="foreignkey")
        batch.drop_column("user_id")
