"""Mark simulated monitoring checks explicitly.

Revision ID: 20261011_0002
Revises: 20260410_0001
"""

import sqlalchemy as sa
from alembic import op


revision = "20261011_0002"
down_revision = "20260410_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("monitoring_checks") as batch_op:
        batch_op.add_column(sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("monitoring_checks") as batch_op:
        batch_op.drop_column("is_simulated")
