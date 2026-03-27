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

    # Pre-warm Redis cache so the first /daily_status request is fast.
    # Runs as a background task — never blocks startup.
    asyncio.ensure_future(_warm_cache())

    yield
    # Shutdown — nothing to clean up


async def _warm_cache() -> None:
    """Pre-fetch live portfolio value on startup to populate Redis cache."""
    await asyncio.sleep(5)  # wait for full app initialisation
    try:
        from app.config import get_default_user_id
        from app.services.portfolio_value import compute_live_portfolio_value
        user_id = get_default_user_id()
        await asyncio.to_thread(compute_live_portfolio_value, user_id)
        logger.info("Cache warmed on startup — portfolio value pre-fetched")
    except Exception as exc:
        logger.warning("Startup cache warm failed (non-fatal): %s", exc)


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
# Cache-Control middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        path = request.url.path
        if "/markets/" in path:
            response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
        elif "/performance/" in path:
            response.headers["Cache-Control"] = "private, max-age=30, stale-while-revalidate=120"
        elif path in ("/daily_status", "/valuation_summary", "/assets/list"):
            response.headers["Cache-Control"] = "private, max-age=30, stale-while-revalidate=60"
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api import alerts, allocation, connections, finance, import_csv, journal, markets, performance, price_history, reports, research, simulation, tax, valuation
app.include_router(allocation.router, prefix="", tags=["allocation"])
app.include_router(valuation.router, prefix="", tags=["valuation"])
app.include_router(performance.router, prefix="", tags=["performance"])
app.include_router(alerts.router, prefix="", tags=["alerts"])
app.include_router(journal.router, prefix="", tags=["journal"])
app.include_router(simulation.router, prefix="", tags=["simulation"])
app.include_router(tax.router, prefix="", tags=["tax"])
app.include_router(reports.router, prefix="", tags=["reports"])
app.include_router(research.router, prefix="", tags=["research"])
app.include_router(markets.router, prefix="/markets", tags=["markets"])
app.include_router(price_history.router, prefix="", tags=["price_history"])
app.include_router(connections.router, prefix="/connections", tags=["connections"])
app.include_router(finance.router, prefix="", tags=["finance"])
app.include_router(import_csv.router, prefix="/import", tags=["import"])

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
