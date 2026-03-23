"""OvelhaInvest FastAPI application entry point — Phase 6."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
]

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
from app.api import alerts, allocation, journal, performance, simulation, valuation
app.include_router(allocation.router, prefix="", tags=["allocation"])
app.include_router(valuation.router, prefix="", tags=["valuation"])
app.include_router(performance.router, prefix="", tags=["performance"])
app.include_router(alerts.router, prefix="", tags=["alerts"])
app.include_router(journal.router, prefix="", tags=["journal"])
app.include_router(simulation.router, prefix="", tags=["simulation"])

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health_check() -> dict:
    """Liveness + dependency check endpoint."""
    supabase_ok = check_supabase_connection()
    return {
        "status": "ok",
        "supabase": "connected" if supabase_ok else "unreachable",
        "version": "6.0.0",
        "env": settings.app_env,
    }


@app.get("/version", tags=["system"])
def version() -> dict:
    """Return API version info."""
    return {"version": "6.0.0", "phase": "6", "env": settings.app_env}


@app.get("/", tags=["system"])
def root() -> dict:
    """Root redirect hint."""
    return {"message": "OvelhaInvest API — see /docs for endpoints"}
