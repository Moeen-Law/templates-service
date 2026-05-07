"""add markdown content to templates

Revision ID: 20260507_0002
Revises: 20260411_0001
Create Date: 2026-05-07 00:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260507_0002"
down_revision = "20260411_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_templates",
        sa.Column(
            "markdown_content",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.drop_column("document_templates", "file_id")
    op.alter_column("document_templates", "markdown_content", server_default=None)


def downgrade() -> None:
    op.add_column(
        "document_templates",
        sa.Column(
            "file_id",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    op.drop_column("document_templates", "markdown_content")
    op.alter_column("document_templates", "file_id", server_default=None)
