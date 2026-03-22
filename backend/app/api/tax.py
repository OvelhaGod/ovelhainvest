"""
Tax API endpoints.

GET  /tax/lots               — All open lots with FIFO/HIFO/Spec ID options
GET  /tax/estimate           — Estimated annual tax liability (US)
GET  /tax/brazil_darf        — Monthly running total vs R$20k exemption
POST /tax/harvest_candidates — Identify loss harvesting opportunities

Phase 8 implementation — stub only.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/tax/lots")
async def get_tax_lots(
    account_id: str | None = None,
    symbol: str | None = None,
    method: str = "hifo",
) -> dict:
    """Return all open tax lots with gain/loss estimates per lot method."""
    raise NotImplementedError("Phase 8")


@router.get("/tax/estimate")
async def get_tax_estimate() -> dict:
    """Return estimated annual US capital gains tax liability."""
    raise NotImplementedError("Phase 8")


@router.get("/tax/brazil_darf")
async def get_brazil_darf(
    year: int | None = None,
    month: int | None = None,
) -> dict:
    """Return Brazil DARF tracker for specified month (defaults to current)."""
    raise NotImplementedError("Phase 8")


@router.post("/tax/harvest_candidates")
async def get_harvest_candidates() -> dict:
    """Return tax-loss harvesting candidates with wash sale risk flags."""
    raise NotImplementedError("Phase 8")
