"""
Decision journal engine: tracks followed/overrode/deferred decisions and backtracks outcomes.

One of the most differentiated features — captures WHY decisions were made,
then measures whether overrides beat or lagged the system recommendation.

Outcome backfill is run by n8n 30d and 90d after each journal entry.

Phase 9 implementation — stub only.
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class JournalActionType(Enum):
    FOLLOWED = "followed"           # system said X, you did X
    OVERRODE = "overrode"           # system said X, you did Y
    DEFERRED = "deferred"           # system said X, you waited
    MANUAL_TRADE = "manual_trade"   # trade not from system recommendation


def log_decision(
    user_id: str,
    action_type: JournalActionType,
    signal_run_id: str | None,
    asset_id: str | None,
    system_recommendation: dict | None,
    actual_action: dict,
    reasoning: str,
) -> dict:
    """
    Persist a decision journal entry.

    Args:
        user_id: User UUID.
        action_type: One of JournalActionType.
        signal_run_id: UUID of the signals_run this decision relates to (if any).
        asset_id: Asset UUID if trade-specific.
        system_recommendation: What the system proposed (from signals_run).
        actual_action: What was actually done.
        reasoning: Free-text explanation.

    Returns:
        Created journal entry dict.
    """
    raise NotImplementedError("Phase 9")


def backfill_outcomes(
    journal_entries: list[dict],
    current_prices: dict[str, float],
    portfolio_return: float,
) -> list[dict]:
    """
    Compute 30d/90d outcomes for journal entries that lack them.

    Run by n8n workflow 30 and 90 days after each entry.
    Computes: (actual outcome) vs (what would have happened following system rec).

    Args:
        journal_entries: Entries missing outcome_30d or outcome_90d.
        current_prices: Current market prices by symbol.
        portfolio_return: Portfolio return since entry date (for context).

    Returns:
        Updated entries with outcome_30d/outcome_90d filled in.
    """
    raise NotImplementedError("Phase 9")


def compute_override_accuracy(
    journal_entries: list[dict],
) -> dict:
    """
    Compute override accuracy statistics.

    Shows: "When you overrode the system, were you right? (30d/90d outcomes)"

    Args:
        journal_entries: All journal entries for the user.

    Returns:
        Dict with:
        - override_count, follow_count, defer_count
        - override_avg_outcome_30d, follow_avg_outcome_30d
        - override_accuracy_vs_system (positive = override beat system)
        - pattern_notes: strings like "You override most often during high-vol periods"
    """
    raise NotImplementedError("Phase 9")


async def generate_pattern_analysis(
    journal_entries: list[dict],
    anthropic_client,  # anthropic.AsyncAnthropic
) -> str:
    """
    Use Claude to generate a monthly pattern analysis from journal data.

    Prompt identifies behavioral patterns in override decisions.

    Args:
        journal_entries: Recent journal entries (last 90 days).
        anthropic_client: Anthropic async client.

    Returns:
        Human-readable pattern analysis string.
    """
    raise NotImplementedError("Phase 9")
