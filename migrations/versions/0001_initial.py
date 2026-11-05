"""Create blog tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("username", sa.String(30), nullable=False), sa.Column("hashed_password", sa.String(255), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("posts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_posts_author_id", "posts", ["author_id"])
    op.create_table("comments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False), sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_comments_post_id", "comments", ["post_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])
    op.create_table("reactions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.UniqueConstraint("post_id", "user_id", name="uq_reaction_post_user"))
    op.create_index("ix_reactions_post_id", "reactions", ["post_id"])
    op.create_index("ix_reactions_user_id", "reactions", ["user_id"])


def downgrade():
    op.drop_index("ix_reactions_user_id", table_name="reactions")
    op.drop_index("ix_reactions_post_id", table_name="reactions")
    op.drop_table("reactions")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_posts_author_id", table_name="posts")
    op.drop_table("posts")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
