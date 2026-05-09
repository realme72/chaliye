"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "riders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(20), unique=True, nullable=False),
        sa.Column("email", sa.String(256), unique=True, nullable=False),
        sa.Column("api_key", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "drivers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("phone", sa.String(20), unique=True, nullable=False),
        sa.Column("email", sa.String(256), unique=True, nullable=False),
        sa.Column("vehicle_type", sa.String(64), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="OFFLINE"),
        sa.Column("rating", sa.Float, nullable=False, server_default="5.0"),
        sa.Column("total_trips", sa.Integer, nullable=False, server_default="0"),
        sa.Column("api_key", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_drivers_status_tier", "drivers", ["status", "tier"])
    op.create_index("ix_drivers_api_key", "drivers", ["api_key"])

    op.create_table(
        "rides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("rider_id", UUID(as_uuid=True), sa.ForeignKey("riders.id"), nullable=False),
        sa.Column("driver_id", UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("pickup_lat", sa.Float, nullable=False),
        sa.Column("pickup_lng", sa.Float, nullable=False),
        sa.Column("pickup_address", sa.String(512), nullable=True),
        sa.Column("destination_lat", sa.Float, nullable=False),
        sa.Column("destination_lng", sa.Float, nullable=False),
        sa.Column("destination_address", sa.String(512), nullable=True),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("payment_method", sa.String(16), nullable=False, server_default="CASH"),
        sa.Column("surge_multiplier", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("estimated_fare", sa.Float, nullable=True),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rides_status", "rides", ["status"])
    op.create_index("ix_rides_rider_id", "rides", ["rider_id"])
    op.create_index("ix_rides_driver_id", "rides", ["driver_id"])
    op.create_index("ix_rides_idempotency_key", "rides", ["idempotency_key"])

    op.create_table(
        "trips",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ride_id", UUID(as_uuid=True), sa.ForeignKey("rides.id"), unique=True, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("distance_km", sa.Float, nullable=True),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("actual_fare", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trips_ride_id", "trips", ["ride_id"])

    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("trip_id", UUID(as_uuid=True), sa.ForeignKey("trips.id"), nullable=False),
        sa.Column("rider_id", UUID(as_uuid=True), sa.ForeignKey("riders.id"), nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("payment_method", sa.String(16), nullable=False),
        sa.Column("psp_reference", sa.String(128), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(128), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payments_trip_id", "payments", ["trip_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("trips")
    op.drop_table("rides")
    op.drop_table("drivers")
    op.drop_table("riders")
