"""Prevent duplicate file imports per user.

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.create_unique_constraint(
            "uq_activities_user_source_external_id",
            ["user_id", "source", "external_source_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_constraint(
            "uq_activities_user_source_external_id",
            type_="unique",
        )
