"""
Allocation engine: sleeve weights, drift detection, vault balances.

Encodes David Swensen / Yale Endowment allocation framework:
- 6 sleeves with target/min/max weights
- Drift threshold 5% triggers rebalance consideration
- Soft rebalance (new money) preferred over hard rebalance (selling)
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.allocation_models import (
    EconomicSeason,
    RegimeState,
    SleeveWeight,
    VaultBalance,
)

logger = logging.getLogger(__name__)

# ── IPS constants (Swensen model) ──────────────────────────────────────────────
SLEEVE_TARGETS: dict[str, dict] = {
    "us_equity":     {"target": 0.45, "min": 0.40, "max": 0.50},
    "intl_equity":   {"target": 0.15, "min": 0.10, "max": 0.20},
    "bonds":         {"target": 0.20, "min": 0.10, "max": 0.30},
    "brazil_equity": {"target": 0.10, "min": 0.05, "max": 0.15},
    "crypto":        {"target": 0.07, "min": 0.05, "max": 0.10},
    "cash":          {"target": 0.03, "min": 0.02, "max": 0.10},
}

DRIFT_THRESHOLD = 0.05  # 5% drift triggers rebalance consideration

# Asset class → sleeve mapping
ASSET_CLASS_TO_SLEEVE: dict[str, str] = {
    "US_equity":     "us_equity",
    "Intl_equity":   "intl_equity",
    "Bond":          "bonds",
    "Brazil_equity": "brazil_equity",
    "Crypto":        "crypto",
    "Cash":          "cash",
    "Bank":          "cash",
    "Benchmark":     "us_equity",  # benchmarks tracked under US equity
}

HIGH_VOL_TRIGGERS = {
    "vix_threshold": 30,
    "equity_daily_move_pct": 0.03,
    "crypto_daily_move_pct": 0.10,
}

DRAWDOWN_THRESHOLDS = {
    "alert": 0.25,
    "pause_automation": 0.40,
}


def map_asset_to_sleeve(asset_class: str) -> str:
    """
    Map asset_class string to sleeve key from SLEEVE_TARGETS.

    Args:
        asset_class: Value from assets.asset_class column.

    Returns:
        Sleeve key (e.g. "us_equity"), defaults to "cash" for unknown classes.
    """
    return ASSET_CLASS_TO_SLEEVE.get(asset_class, "cash")


def compute_account_values(
    holdings: list[dict],
    prices: dict[str, float],
    fx_rate: float,
) -> dict[str, float]:
    """
    Compute total USD market value per account.

    Args:
        holdings: List of holding dicts (symbol, currency, quantity, account_id, account_name).
        prices: Dict of symbol → price in native currency.
        fx_rate: USD/BRL rate (BRL per 1 USD).

    Returns:
        Dict of account_id → total USD value.
    """
    from app.services.fx_engine import normalize_to_usd

    account_values: dict[str, float] = {}
    for h in holdings:
        account_id = h.get("account_id", "unknown")
        symbol = h.get("symbol", "")
        qty = float(h.get("quantity", 0))
        currency = h.get("currency", "USD")
        price = prices.get(symbol, 0.0)
        native_value = qty * price
        usd_value = normalize_to_usd(native_value, fx_rate) if currency == "BRL" else native_value
        account_values[account_id] = account_values.get(account_id, 0.0) + usd_value

    return account_values


def compute_sleeve_values(
    holdings: list[dict],
    assets: dict[str, dict],
    prices: dict[str, float],
    fx_rate: float,
) -> dict[str, float]:
    """
    Compute total USD value per sleeve based on holdings.

    Args:
        holdings: List of holding dicts (symbol, currency, quantity, asset_class).
        assets: Dict of symbol → asset dict (with asset_class, currency).
        prices: Dict of symbol → price in native currency.
        fx_rate: USD/BRL rate.

    Returns:
        Dict of sleeve_key → total USD value.
    """
    from app.services.fx_engine import normalize_to_usd

    sleeve_values: dict[str, float] = {k: 0.0 for k in SLEEVE_TARGETS}

    for h in holdings:
        symbol = h.get("symbol", "")
        qty = float(h.get("quantity", 0))
        asset = assets.get(symbol, {})
        asset_class = asset.get("asset_class") or h.get("asset_class", "")
        currency = asset.get("currency") or h.get("currency", "USD")
        price = prices.get(symbol, 0.0)
        native_value = qty * price

        usd_value = normalize_to_usd(native_value, fx_rate) if currency == "BRL" else native_value
        sleeve = map_asset_to_sleeve(asset_class)
        if sleeve in sleeve_values:
            sleeve_values[sleeve] += usd_value
        else:
            sleeve_values["cash"] = sleeve_values.get("cash", 0.0) + usd_value

    return sleeve_values


def compute_current_sleeve_weights(
    sleeve_values: dict[str, float],
) -> dict[str, float]:
    """
    Compute fractional weight per sleeve from USD values.

    Args:
        sleeve_values: Dict of sleeve_key → USD value.

    Returns:
        Dict of sleeve_key → fraction (0-1). Sums to 1.0 if total > 0.
    """
    total = sum(sleeve_values.values())
    if total <= 0:
        return {k: 0.0 for k in sleeve_values}
    return {k: v / total for k, v in sleeve_values.items()}


def detect_drift_vs_targets(
    current_weights: dict[str, float],
    sleeve_values: dict[str, float],
    config: dict | None = None,
) -> list[SleeveWeight]:
    """
    Compare current sleeve weights against IPS targets, flag drift breaches.

    Args:
        current_weights: Dict of sleeve_key → current fraction.
        sleeve_values: Dict of sleeve_key → USD value.
        config: Optional strategy config override (uses IPS defaults if None).

    Returns:
        List of SleeveWeight models sorted by abs(drift) descending.
    """
    targets = SLEEVE_TARGETS
    if config and "sleeve_targets" in config:
        targets = config["sleeve_targets"]

    results: list[SleeveWeight] = []
    for sleeve, spec in targets.items():
        current = current_weights.get(sleeve, 0.0)
        target = spec["target"]
        drift = current - target

        results.append(SleeveWeight(
            sleeve=sleeve,
            current_weight=round(current, 6),
            target_weight=target,
            min_weight=spec["min"],
            max_weight=spec["max"],
            drift=round(drift, 6),
            drift_pct=round(drift * 100, 2),
            is_breached=abs(drift) >= DRIFT_THRESHOLD,
            current_value_usd=round(sleeve_values.get(sleeve, 0.0), 2),
        ))

    return sorted(results, key=lambda x: abs(x.drift), reverse=True)


def compute_vault_balances(
    vaults: list[dict],
    account_balances: dict[str, float],
) -> list[VaultBalance]:
    """
    Compute vault balance status from vault records and account balances.

    Args:
        vaults: List of vault dicts from DB (vault_type, min_balance, account_id, etc.).
        account_balances: Dict of account_id → USD balance.

    Returns:
        List of VaultBalance models.
    """
    vault_type_config = {
        "future_investments": {"investable": True,  "approval_required": False},
        "opportunity":        {"investable": True,  "approval_required": True},
        "emergency":          {"investable": False, "approval_required": False},
    }

    results: list[VaultBalance] = []
    for vault in vaults:
        vault_type = vault.get("vault_type", "")
        account_id = vault.get("account_id", "")
        balance = account_balances.get(account_id, 0.0)
        min_bal = vault.get("min_balance")
        cfg = vault_type_config.get(vault_type, {"investable": False, "approval_required": False})

        progress = None
        if min_bal and min_bal > 0:
            progress = min(round(balance / min_bal, 4), 1.0)

        results.append(VaultBalance(
            vault_type=vault_type,
            balance_usd=round(balance, 2),
            min_balance=min_bal,
            is_investable=cfg["investable"],
            approval_required=cfg["approval_required"],
            progress_pct=progress,
        ))

    return results


def get_regime_state(
    vix: float,
    equity_move_pct: float,
    crypto_move_pct: float,
    portfolio_drawdown_pct: float = 0.0,
    config: dict | None = None,
) -> RegimeState:
    """
    Classify current volatility regime based on VIX, price moves, and drawdown.

    Dalio-inspired: high VIX + large equity moves → defer DCA 1-3 days.
    But allow opportunity deployment if price is sufficiently discounted.

    Args:
        vix: Current VIX index value.
        equity_move_pct: Today's equity market move (positive = up).
        crypto_move_pct: Today's crypto market move.
        portfolio_drawdown_pct: Current portfolio drawdown from peak (negative = down).
        config: Optional strategy config override.

    Returns:
        RegimeState enum value.
    """
    triggers = HIGH_VOL_TRIGGERS
    if config and "high_vol_triggers" in config:
        triggers = config["high_vol_triggers"]

    dd = abs(portfolio_drawdown_pct)
    if dd >= DRAWDOWN_THRESHOLDS["pause_automation"]:
        return RegimeState.PAUSED

    is_high_vol = (
        vix >= triggers["vix_threshold"]
        or abs(equity_move_pct) >= triggers["equity_daily_move_pct"]
        or abs(crypto_move_pct) >= triggers["crypto_daily_move_pct"]
    )

    if is_high_vol:
        # In high-vol, opportunity mode if there are discounted assets
        # (opportunity_detector will evaluate; regime stays HIGH_VOL unless explicitly upgraded)
        return RegimeState.HIGH_VOL

    return RegimeState.NORMAL
