"""OvelhaInvest FastAPI application entry point."""

import logging
import sys

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
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="OvelhaInvest API",
    description="Thiago Wealth OS — personal robo-advisor backend",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ---------------------------------------------------------------------------
# CORS — allow local frontend dev server + production origin
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
from app.api import allocation, valuation
app.include_router(allocation.router, prefix="", tags=["allocation"])
app.include_router(valuation.router, prefix="", tags=["valuation"])
# Future phases:
# from app.api import backtest, performance, simulation, tax, alerts, reports
# app.include_router(performance.router, tags=["performance"])

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
        "version": "1.0.0",
        "env": settings.app_env,
    }


@app.get("/version", tags=["system"])
def version() -> dict:
    """Return API version info."""
    return {"version": "3.0.0", "phase": "3", "env": settings.app_env}


@app.get("/", tags=["system"])
def root() -> dict:
    """Root redirect hint."""
    return {"message": "OvelhaInvest API — see /docs for endpoints"}
