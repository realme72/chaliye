"""
Seed script — creates sample drivers and riders for manual testing.
Run: python seed.py
"""
from __future__ import annotations

import asyncio
import secrets
import uuid

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.core.base import Base
import app.riders.models, app.drivers.models, app.rides.models, app.trips.models, app.payments.models  # noqa: F401
from app.drivers.models import Driver
from app.riders.models import Rider

engine = create_async_engine(settings.database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        riders = [
            Rider(
                id=uuid.uuid4(),
                name="Priya Sharma",
                phone="+919876543210",
                email="priya@example.com",
                api_key=secrets.token_hex(16),
            ),
            Rider(
                id=uuid.uuid4(),
                name="Rahul Gupta",
                phone="+919876543211",
                email="rahul@example.com",
                api_key=secrets.token_hex(16),
            ),
        ]
        session.add_all(riders)

        drivers = [
            Driver(
                id=uuid.uuid4(),
                name="Suresh Kumar",
                phone="+919876500001",
                email="suresh@example.com",
                vehicle_type="SEDAN",
                tier="ECONOMY",
                status="OFFLINE",
                api_key=secrets.token_hex(16),
            ),
            Driver(
                id=uuid.uuid4(),
                name="Rajesh Verma",
                phone="+919876500002",
                email="rajesh@example.com",
                vehicle_type="SUV",
                tier="PREMIUM",
                status="OFFLINE",
                api_key=secrets.token_hex(16),
            ),
            Driver(
                id=uuid.uuid4(),
                name="Amit Patel",
                phone="+919876500003",
                email="amit@example.com",
                vehicle_type="LUXURY_SEDAN",
                tier="LUXURY",
                status="OFFLINE",
                api_key=secrets.token_hex(16),
            ),
        ]
        session.add_all(drivers)
        await session.commit()

        print("\n=== Seeded successfully ===\n")
        print("RIDERS")
        for r in riders:
            print(f"  id={r.id}  api_key={r.api_key}  name={r.name}")

        print("\nDRIVERS")
        for d in drivers:
            print(f"  id={d.id}  api_key={d.api_key}  tier={d.tier}  name={d.name}")
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
