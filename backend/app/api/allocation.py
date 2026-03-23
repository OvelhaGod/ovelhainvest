"""
Allocation API router.

POST /run_allocation — run full portfolio engine cycle, write signals_run
GET  /daily_status   — current portfolio status, no write
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.repositories import accounts as accounts_repo
from app.db.repositories import holdings as holdings_repo
from app.db.repositories import signals as signals_repo
from app.db.repositories import snapshots as snapshots_repo
from app.db.repositories import valuations as valuations_repo
from app.schemas.allocation_models import (
    AllocationRunRequest,
    AllocationRunResponse,
    DailyStatusResponse,
    EconomicSeason,
    RegimeState,
)
from app.services import allocation_engine, opportunity_detector, rebalancing
from app.services.alert_engine import BUILT_IN_ALERT_RULES
from app.services.fx_engine import fetch_usd_brl_rate, normalize_to_brl
from app.services.market_data import fetch_current_prices
from app.services.volatility_regime import (
    detect_volatility_regime,
    fetch_vix,
    get_economic_season,
    get_factor_weights_for_regime,
    should_defer_core_dca,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Hard-coded single user for Phase 2 (multi-user in future phases)
DEFAULT_USER_ID_HEADER = "x-user-id"


def _get_user_id(user_id: str = Query(default=None)) -> str:
    """Extract user_id from query param. Single-user app — returns placeholder if missing."""
    return user_id or "00000000-0000-0000-0000-000000000001"


@router.post("/run_allocation", response_model=AllocationRunResponse)
def run_allocation(
    body: AllocationRunRequest,
    user_id: str = Depends(_get_user_id),
) -> AllocationRunResponse:
    """
    Execute the full portfolio engine cycle:

    1. Load accounts + holdings
    2. Fetch live prices + FX rate
    3. Compute sleeve weights + drift
    4. Detect volatility regime + economic season
    5. Propose soft rebalance trades
    6. Evaluate opportunity tiers for held assets
    7. Write signals_run record
    8. Return structured response

    AI validation happens async (Phase 5) — stored in signals_run later.
    """
    run_id = str(uuid.uuid4())
    run_timestamp = datetime.now(timezone.utc)
    uid = body.user_id or user_id
    logger.info("run_allocation start run_id=%s user=%s event=%s", run_id, uid, body.event_type)

    try:
        # ── 1. Load accounts + holdings ────────────────────────────────────
        accounts = accounts_repo.get_accounts(uid)
        if not accounts:
            raise HTTPException(status_code=404, detail="No accounts found for user")

        holdings = holdings_repo.get_holdings(uid)
        vaults = accounts_repo.get_vaults(uid)

        # ── 2. Fetch prices + FX ───────────────────────────────────────────
        symbols = list({h["symbol"] for h in holdings if h.get("symbol")})
        # Add market proxies for regime detection
        symbols_for_prices = symbols + ["SPY", "BTC-USD"]
        prices = fetch_current_prices(symbols_for_prices)
        fx_rate = fetch_usd_brl_rate()

        # ── 3. Sleeve weights + drift ──────────────────────────────────────
        assets_map = {h["symbol"]: h for h in holdings}
        sleeve_values = allocation_engine.compute_sleeve_values(
            holdings, assets_map, prices, fx_rate
        )
        total_value_usd = sum(sleeve_values.values())
        sleeve_weights_dict = allocation_engine.compute_current_sleeve_weights(sleeve_values)
        drift_weights = allocation_engine.detect_drift_vs_targets(
            sleeve_weights_dict, sleeve_values, config=None
        )

        # ── 4. Regime + season ─────────────────────────────────────────────
        vix = fetch_vix()
        # Get today's moves from price deltas (simplified: use SPY + BTC)
        spy_price = prices.get("SPY", 0)
        btc_price = prices.get("BTC-USD", 0)
        equity_move = 0.0  # Would compute vs yesterday snapshot; 0 for now
        crypto_move = 0.0

        # Get latest snapshot for drawdown
        latest_snapshot = snapshots_repo.get_latest_snapshot(uid)
        portfolio_drawdown = 0.0
        if latest_snapshot:
            portfolio_drawdown = latest_snapshot.get("drawdown_from_peak_pct", 0.0) or 0.0

        regime = detect_volatility_regime(
            vix, equity_move, crypto_move, portfolio_drawdown
        )
        economic_season = get_economic_season()

        # ── 5. DCA deferral check ──────────────────────────────────────────
        defer_dca, defer_days = should_defer_core_dca(regime)

        # ── 6. Vault balances ──────────────────────────────────────────────
        account_values = allocation_engine.compute_account_values(holdings, prices, fx_rate)
        vault_balances = allocation_engine.compute_vault_balances(vaults, account_values)

        # ── 7. Soft rebalance proposals ────────────────────────────────────
        proposed_trades = []
        if not defer_dca or body.force_hard_rebalance:
            # Find available cash from future_investments vault
            future_vault = next(
                (v for v in vault_balances if v.vault_type == "future_investments"), None
            )
            available_cash = future_vault.balance_usd if future_vault else 0.0

            # Build assets_by_sleeve from holdings
            assets_by_sleeve: dict[str, list[dict]] = {}
            for h in holdings:
                sleeve = allocation_engine.map_asset_to_sleeve(h.get("asset_class", ""))
                if sleeve not in assets_by_sleeve:
                    assets_by_sleeve[sleeve] = []
                if not any(a["symbol"] == h["symbol"] for a in assets_by_sleeve[sleeve]):
                    assets_by_sleeve[sleeve].append(h)

            if available_cash >= 50:
                soft_trades = rebalancing.propose_soft_rebalance_trades(
                    drift_weights=drift_weights,
                    available_cash_usd=available_cash,
                    assets_by_sleeve=assets_by_sleeve,
                    prices=prices,
                    portfolio_value_usd=total_value_usd,
                    preferred_accounts=accounts,
                )
                proposed_trades.extend(soft_trades)

        # ── 8. Opportunity tier evaluation ────────────────────────────────
        latest_valuations = valuations_repo.get_latest_valuations()
        val_map = {v.get("symbol", ""): v for v in latest_valuations}

        opportunity_vault = next(
            (v for v in vault_balances if v.vault_type == "opportunity"), None
        )
        opp_vault_balance = opportunity_vault.balance_usd if opportunity_vault else 0.0

        # Count existing opportunity events this year (simplified: 0 for now)
        events_this_year = 0

        for h in holdings:
            sym = h.get("symbol", "")
            val = val_map.get(sym)
            if not val:
                continue

            drawdown = val.get("drawdown_from_6_12m_high_pct", 0.0) or 0.0
            mos = val.get("margin_of_safety_pct", 0.0) or 0.0

            if opportunity_detector.evaluate_tier_1_trigger(
                drawdown, mos, events_this_year
            ):
                deploy = opportunity_detector.compute_opportunity_vault_deployment(
                    opp_vault_balance, 1, total_value_usd
                )
                if deploy >= 50:
                    opp_account = accounts[0]  # Simplified: use first account
                    opp_trade = opportunity_detector.build_opportunity_trade(
                        h, deploy, 1, mos, opp_account
                    )
                    proposed_trades.append(opp_trade)
                    events_this_year += 1

        # ── 9. Flag approval requirements ─────────────────────────────────
        proposed_trades = rebalancing.flag_approval_required(proposed_trades)
        approval_count = sum(1 for t in proposed_trades if t.requires_approval)

        # ── 10. Determine run status ───────────────────────────────────────
        status = "needs_approval" if approval_count > 0 else "auto_ok"

        # ── 11. Write signals_run to DB (pre-AI, so we have a run_id) ─────
        total_value_brl = normalize_to_brl(total_value_usd, fx_rate)
        run_record = {
            "id": run_id,
            "user_id": uid,
            "run_timestamp": run_timestamp.isoformat(),
            "event_type": body.event_type,
            "inputs_summary": {
                "vix": vix,
                "regime": regime.value,
                "economic_season": economic_season.value,
                "total_value_usd": round(total_value_usd, 2),
                "usd_brl_rate": round(fx_rate, 4),
                "deferred_dca": defer_dca,
                "factor_weights": get_factor_weights_for_regime(economic_season),
            },
            "proposed_trades": [t.model_dump() for t in proposed_trades],
            "ai_validation_summary": None,
            "status": status,
            "notes": body.notes,
        }
        signals_repo.create_signals_run(run_record)

        # ── 12. AI Advisor validation (Phase 5) ────────────────────────────
        import asyncio
        from app.services import ai_advisor
        from app.services.alert_engine import evaluate_all_rules, dispatch_alert
        from app.db.repositories.valuations import get_valuation_summary_stats

        ai_response = None
        ai_summary_dict: dict | None = None
        ai_framework_dict: dict | None = None
        alerts_dispatched = 0

        try:
            # Build AI payload
            val_stats = {}
            try:
                val_stats = get_valuation_summary_stats() or {}
            except Exception:
                pass

            latest_snapshot = snapshots_repo.get_latest_snapshot(uid)
            perf_snap = {}
            if latest_snapshot:
                perf_snap = {
                    "twr_ytd": latest_snapshot.get("portfolio_return_ytd"),
                    "sharpe": latest_snapshot.get("sharpe_ratio"),
                    "sortino": latest_snapshot.get("sortino_ratio"),
                    "max_drawdown": latest_snapshot.get("drawdown_from_peak_pct"),
                    "volatility": latest_snapshot.get("volatility_annualized"),
                }

            ai_payload = ai_advisor.build_ai_payload(
                run_context={
                    "timestamp": run_timestamp.isoformat(),
                    "event_type": body.event_type,
                    "regime": regime.value,
                    "economic_season": economic_season.value,
                    "vix": vix,
                    "notes": body.notes,
                },
                portfolio_snapshot={
                    "total_value_usd": round(total_value_usd, 2),
                    "total_value_brl": round(total_value_brl, 2),
                    "sleeve_weights": [w.model_dump() for w in drift_weights],
                    "risk_parity_weights": {},
                    "correlation_matrix": {},
                    "concentration_top5": [],
                },
                valuation_snapshot={
                    "top_opportunities": val_stats.get("top_opportunities", []),
                    "tier_opportunities": [],
                    "mos_distribution": val_stats.get("margin_of_safety_distribution", {}),
                    "assets_scored": val_stats.get("assets_scored", 0),
                },
                performance_snapshot=perf_snap,
                proposed_trades=[t.model_dump() for t in proposed_trades],
                news_and_research={"macro_summary": "", "macro_regime": regime.value},
                active_config={},
            )

            # Call Claude API with 30s timeout
            ai_response = asyncio.get_event_loop().run_until_complete(
                asyncio.wait_for(
                    ai_advisor.call_ai_advisor(ai_payload, signals_run_id=run_id),
                    timeout=30.0,
                )
            )
            ai_summary_dict = ai_response.model_dump()
            ai_framework_dict = ai_response.investment_framework_check.model_dump()

            # Update signals_run with AI result
            try:
                from app.db.supabase_client import get_supabase_client
                get_supabase_client().table("signals_runs").update(
                    {"ai_validation_summary": ai_summary_dict}
                ).eq("id", run_id).execute()
            except Exception as exc:
                logger.debug("signals_run AI update failed (non-critical): %s", exc)

            # ── 13. Alert evaluation + dispatch ───────────────────────────
            current_max_dd = abs(perf_snap.get("max_drawdown") or 0.0)
            portfolio_state = {
                "max_drawdown": -current_max_dd,
                "sleeve_weights": [w.model_dump() for w in drift_weights],
                "opportunity_tier_1": any(
                    t.opportunity_tier == 1 for t in proposed_trades
                ),
                "opportunity_tier_2": any(
                    t.opportunity_tier == 2 for t in proposed_trades
                ),
                "held_assets_at_sell_target": [],
                "darf_progress_pct": 0.0,
                "usd_brl_30d_change": 0.0,
                "correlation_pairs": [],
                "recent_deposits": [],
            }
            triggered_alerts = evaluate_all_rules(
                portfolio_state=portfolio_state,
                alert_rules=BUILT_IN_ALERT_RULES,
            )

            loop = asyncio.get_event_loop()
            for alert in triggered_alerts:
                keyboard = None
                if alert.get("type") == "opportunity":
                    keyboard = [
                        [
                            {"text": "Approve", "callback_data": f"approve:{run_id}"},
                            {"text": "Reject", "callback_data": f"reject:{run_id}"},
                        ]
                    ]
                try:
                    ok = loop.run_until_complete(dispatch_alert(alert, keyboard=keyboard))
                    if ok:
                        alerts_dispatched += 1
                except Exception as exc:
                    logger.debug("Alert dispatch failed (non-critical): %s", exc)

        except asyncio.TimeoutError:
            logger.warning("AI advisor timed out for run_id=%s — proceeding without AI", run_id)
            ai_summary_dict = ai_advisor.FALLBACK_RESPONSE.model_dump()
            ai_summary_dict["explanation_for_user"]["short_summary"] = (
                "AI validation timed out — engine recommendation stands."
            )
        except Exception as exc:
            logger.error("AI advisor/alert step failed (non-critical) run_id=%s: %s", run_id, exc)

        logger.info(
            "run_allocation complete run_id=%s trades=%d approvals=%d alerts=%d",
            run_id, len(proposed_trades), approval_count, alerts_dispatched,
        )

        return AllocationRunResponse(
            run_id=run_id,
            run_timestamp=run_timestamp,
            event_type=body.event_type,
            regime_state=regime,
            economic_season=economic_season,
            sleeve_weights=drift_weights,
            vault_balances=vault_balances,
            proposed_trades=proposed_trades,
            total_value_usd=round(total_value_usd, 2),
            total_value_brl=round(total_value_brl, 2),
            usd_brl_rate=round(fx_rate, 4),
            approval_required_count=approval_count,
            deferred_dca=defer_dca,
            deferred_reason=f"High volatility — deferred {defer_days} days" if defer_dca else None,
            status=status,
            ai_validation_summary=ai_summary_dict,
            ai_framework_check=ai_framework_dict,
            alerts_dispatched=alerts_dispatched,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("run_allocation failed run_id=%s: %s", run_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Allocation run failed: {exc}")


@router.get("/daily_status", response_model=DailyStatusResponse)
def daily_status(user_id: str = Depends(_get_user_id)) -> DailyStatusResponse:
    """
    Return current portfolio status without triggering a new signals run.

    Reads from latest portfolio_snapshot (updated daily by n8n or run_allocation).
    Falls back to live market data if no snapshot available.
    """
    logger.info("daily_status user=%s", user_id)

    try:
        # Latest snapshot
        snapshot = snapshots_repo.get_latest_snapshot(user_id)
        last_run_ts = signals_repo.get_last_run_timestamp(user_id)
        pending = signals_repo.get_pending_approvals(user_id)

        if snapshot:
            total_value_usd = float(snapshot.get("total_value_usd", 0))
            total_value_brl = float(snapshot.get("total_value_brl") or 0)
            usd_brl_rate = float(snapshot.get("usd_brl_rate") or 5.70)
            sleeve_weights_raw = snapshot.get("sleeve_weights") or {}
            ytd_twr = snapshot.get("portfolio_return_ytd")
            max_dd = snapshot.get("drawdown_from_peak_pct")
            snap_date_str = snapshot.get("snapshot_date")
            from datetime import date as ddate
            snap_date = ddate.fromisoformat(str(snap_date_str)) if snap_date_str else None
        else:
            # No snapshot yet — fetch live
            accounts = accounts_repo.get_accounts(user_id)
            holdings = holdings_repo.get_holdings(user_id)
            symbols = list({h["symbol"] for h in holdings if h.get("symbol")})
            prices = fetch_current_prices(symbols) if symbols else {}
            fx_rate = fetch_usd_brl_rate()
            assets_map = {h["symbol"]: h for h in holdings}
            sleeve_values = allocation_engine.compute_sleeve_values(
                holdings, assets_map, prices, fx_rate
            )
            total_value_usd = sum(sleeve_values.values())
            usd_brl_rate = fx_rate
            total_value_brl = normalize_to_brl(total_value_usd, fx_rate)
            sleeve_weights_raw = {}
            ytd_twr = None
            max_dd = None
            snap_date = None

        # Rebuild sleeve weights from snapshot or compute live
        accounts = accounts_repo.get_accounts(user_id)
        holdings = holdings_repo.get_holdings(user_id)
        vaults = accounts_repo.get_vaults(user_id)

        symbols = list({h["symbol"] for h in holdings if h.get("symbol")})
        prices = fetch_current_prices(symbols) if symbols else {}
        fx_rate = fetch_usd_brl_rate()

        assets_map = {h["symbol"]: h for h in holdings}
        sleeve_values = allocation_engine.compute_sleeve_values(
            holdings, assets_map, prices, fx_rate
        )
        if not total_value_usd:
            total_value_usd = sum(sleeve_values.values())
        sleeve_weights_dict = allocation_engine.compute_current_sleeve_weights(sleeve_values)
        drift_weights = allocation_engine.detect_drift_vs_targets(
            sleeve_weights_dict, sleeve_values
        )

        account_values = allocation_engine.compute_account_values(holdings, prices, fx_rate)
        vault_balances = allocation_engine.compute_vault_balances(vaults, account_values)

        # Regime
        vix = fetch_vix()
        regime = detect_volatility_regime(vix, 0.0, 0.0, float(max_dd or 0))
        economic_season = get_economic_season()

        # ── Phase 4 — pull performance metrics from snapshot history ────────
        import pandas as _pd
        from app.db.repositories.snapshots import get_snapshot_history
        from app.services.performance_engine import compute_sharpe

        ytd_vs_benchmark: float | None = None
        sharpe_12mo: float | None = None
        max_dd_current: float | None = None

        try:
            recent_snaps = get_snapshot_history(user_id, days=365)
            if len(recent_snaps) >= 20:
                snap_values = _pd.Series(
                    [float(s["total_value_usd"]) for s in recent_snaps],
                    index=_pd.to_datetime([s["snapshot_date"] for s in recent_snaps]),
                ).sort_index()
                snap_returns = snap_values.pct_change().dropna()
                sharpe_12mo = round(compute_sharpe(snap_returns), 3)

                # Current drawdown from peak
                peak = float(snap_values.max())
                latest_v = float(snap_values.iloc[-1])
                if peak > 0:
                    max_dd_current = round((latest_v - peak) / peak, 4)
        except Exception as _pe_exc:
            logger.debug("Phase 4 perf metrics failed (non-critical): %s", _pe_exc)

        return DailyStatusResponse(
            total_value_usd=round(total_value_usd, 2),
            total_value_brl=round(normalize_to_brl(total_value_usd, usd_brl_rate), 2),
            usd_brl_rate=round(usd_brl_rate, 4),
            sleeve_weights=drift_weights,
            vault_balances=vault_balances,
            regime_state=regime,
            economic_season=economic_season,
            pending_approvals=len(pending),
            last_run_timestamp=last_run_ts,
            today_pnl_usd=None,
            today_pnl_pct=None,
            ytd_return_twr=float(ytd_twr) if ytd_twr else None,
            max_drawdown_pct=float(max_dd) if max_dd else None,
            portfolio_snapshot_date=snap_date,
            ytd_vs_benchmark=ytd_vs_benchmark,
            sharpe_trailing_12mo=sharpe_12mo,
            max_drawdown_current=max_dd_current,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("daily_status failed user=%s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Daily status failed: {exc}")
