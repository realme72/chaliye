from __future__ import annotations

"""
Chaliye — Ride-Hailing API
Run via PyCharm:  python main.py
Run via CLI:      uvicorn main:app --reload
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.base import Base
from app.core.database import engine
from app.core.redis_client import close_redis, get_redis
from app.middleware import AuthMiddleware, LoggerMiddleware, RateLimiterMiddleware, configure_logging

# Import all models so SQLAlchemy registers them with Base.metadata before create_all
import app.riders.models  # noqa: F401
import app.drivers.models  # noqa: F401
import app.rides.models    # noqa: F401
import app.trips.models    # noqa: F401
import app.payments.models # noqa: F401

from app.rides.router import router as rides_router
from app.drivers.router import router as drivers_router
from app.trips.router import router as trips_router
from app.payments.router import router as payments_router

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await get_redis()

    yield

    await close_redis()
    await engine.dispose()


app = FastAPI(
    title="Chaliye — Ride Hailing API",
    version="1.0.0",
    description=(
        "Multi-tenant ride-hailing platform. "
        "6 core endpoints covering the full ride lifecycle: "
        "request → match → accept → trip → payment."
    ),
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggerMiddleware)

PREFIX = "/v1"
app.include_router(rides_router, prefix=PREFIX)
app.include_router(drivers_router, prefix=PREFIX)
app.include_router(trips_router, prefix=PREFIX)
app.include_router(payments_router, prefix=PREFIX)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
    for path in schema["paths"].values():
        for operation in path.values():
            operation.setdefault("security", [{"ApiKeyAuth": []}])
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
