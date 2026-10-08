"""Create the initial BizExpense schema."""

from alembic import op
import sqlalchemy as sa

revision = "20260930_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("abn", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])
    op.create_table(
        "uploaded_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("expense_categories.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("uploaded_documents.id"), unique=True),
        sa.Column("invoice_number", sa.String(100)),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("gst_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("ocr_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("expenses")
    op.drop_table("uploaded_documents")
    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_table("expense_categories")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
