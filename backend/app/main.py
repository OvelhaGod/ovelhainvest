"""OvelhaInvest FastAPI application entry point — Phase 6."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.db.supabase_client import check_supabase_connection

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG if not settings.is_production else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — register Telegram webhook in production
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Startup
    if settings.is_production and settings.telegram_enabled:
        try:
            from app.services.alert_engine import register_telegram_webhook
            ok = await register_telegram_webhook(settings.app_base_url)
            if ok:
                logger.info("Telegram webhook registered on startup")
            else:
                logger.warning("Telegram webhook registration failed on startup")
        except Exception as exc:
            logger.warning("Telegram webhook startup error (non-critical): %s", exc)
    yield
    # Shutdown — nothing to clean up


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="OvelhaInvest API",
    description="Thiago Wealth OS — personal robo-advisor backend",
    version="6.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://10.0.0.201:3000",
    "http://10.0.0.201:3002",
    "https://invest.ovelha.us",
    "https://investapi.ovelha.us",
]

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api import alerts, allocation, journal, performance, reports, simulation, tax, valuation
app.include_router(allocation.router, prefix="", tags=["allocation"])
app.include_router(valuation.router, prefix="", tags=["valuation"])
app.include_router(performance.router, prefix="", tags=["performance"])
app.include_router(alerts.router, prefix="", tags=["alerts"])
app.include_router(journal.router, prefix="", tags=["journal"])
app.include_router(simulation.router, prefix="", tags=["simulation"])
app.include_router(tax.router, prefix="", tags=["tax"])
app.include_router(reports.router, prefix="", tags=["reports"])

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Liveness + dependency check — returns live connectivity status for all services."""
    from datetime import datetime, timezone
    supabase_ok = check_supabase_connection()

    redis_status = "unconfigured"
    try:
        from app.db.redis_client import get_redis_client
        r = get_redis_client()
        if r:
            r.ping()
            redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)[:40]}"

    overall = "ok" if supabase_ok else "degraded"
    return {
        "status": overall,
        "supabase": "connected" if supabase_ok else "unreachable",
        "redis": redis_status,
        "version": "1.2.0",
        "env": settings.app_env,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/version", tags=["system"])
def version() -> dict:
    """Return API version info."""
    return {"version": "1.2.0", "phase": "6", "env": settings.app_env}


@app.get("/", tags=["system"])
def root() -> dict:
    """Root redirect hint."""
    return {"message": "OvelhaInvest API — see /docs for endpoints"}
