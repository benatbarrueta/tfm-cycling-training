"""Add perceived exertion and separate estimated-load summaries.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("activities") as batch_op:
        batch_op.add_column(sa.Column("perceived_exertion", sa.Integer(), nullable=True))
    with op.batch_alter_table("weekly_reviews") as batch_op:
        batch_op.add_column(
            sa.Column("registered_rpe_load", sa.Float(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("activities_with_rpe_load", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("activities_without_load", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("weekly_reviews") as batch_op:
        batch_op.drop_column("activities_without_load")
        batch_op.drop_column("activities_with_rpe_load")
        batch_op.drop_column("registered_rpe_load")
    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_column("perceived_exertion")
