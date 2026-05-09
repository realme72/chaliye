"""Drop idempotency_key from payments; idempotency handled by Redis

Revision ID: 002
Revises: 001
Create Date: 2026-05-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_payments_idempotency_key", table_name="payments")
    op.drop_constraint("payments_idempotency_key_key", "payments", type_="unique")
    op.drop_column("payments", "idempotency_key")
    op.create_index(
        "ix_payments_trip_rider_method",
        "payments",
        ["trip_id", "rider_id", "payment_method"],
    )


def downgrade() -> None:
    op.drop_index("ix_payments_trip_rider_method", table_name="payments")
    op.add_column(
        "payments",
        sa.Column("idempotency_key", sa.String(128), nullable=False, server_default=""),
    )
    op.create_unique_constraint("payments_idempotency_key_key", "payments", ["idempotency_key"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])
