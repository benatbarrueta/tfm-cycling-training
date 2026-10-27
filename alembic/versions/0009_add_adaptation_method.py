"""Record the weekly adaptation method and median RPE.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("weekly_reviews") as batch_op:
        batch_op.add_column(sa.Column("median_perceived_exertion", sa.Float()))
        batch_op.add_column(
            sa.Column(
                "adaptation_method",
                sa.String(length=32),
                nullable=False,
                server_default="INSUFFICIENT_DATA",
            )
        )
    with op.batch_alter_table("adaptation_events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "adaptation_method",
                sa.String(length=32),
                nullable=False,
                server_default="INSUFFICIENT_DATA",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("adaptation_events") as batch_op:
        batch_op.drop_column("adaptation_method")
    with op.batch_alter_table("weekly_reviews") as batch_op:
        batch_op.drop_column("adaptation_method")
        batch_op.drop_column("median_perceived_exertion")
