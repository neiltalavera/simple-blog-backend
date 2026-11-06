"""Add email-bound invite requests and lockout tracking."""
from alembic import op
import sqlalchemy as sa

revision = "0002_access_requests"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("invite_code_hash", sa.String(64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_access_requests_email", "access_requests", ["email"], unique=True)


def downgrade():
    op.drop_index("ix_access_requests_email", table_name="access_requests")
    op.drop_table("access_requests")
