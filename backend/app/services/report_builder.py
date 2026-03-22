"""
PDF report builder using WeasyPrint.

Generates daily, monthly, and annual portfolio reports.
Reports stored in Supabase Storage (or local filesystem in dev).

Phase 9 implementation — stub only.
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ReportType(Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    ANNUAL = "annual"


def build_report_payload(
    user_id: str,
    report_type: ReportType,
    period_start: str,
    period_end: str,
    portfolio_snapshot: dict,
    performance_data: dict,
    signals_summary: dict,
    ai_commentary: str,
) -> dict:
    """
    Assemble all data needed for a PDF report.

    Args:
        user_id: User UUID.
        report_type: Daily, monthly, or annual.
        period_start: ISO date string.
        period_end: ISO date string.
        portfolio_snapshot: Latest portfolio snapshot data.
        performance_data: Returns, ratios, attribution for period.
        signals_summary: Summary of signals_runs for period.
        ai_commentary: AI-generated narrative summary.

    Returns:
        Report payload dict ready for PDF generation.
    """
    raise NotImplementedError("Phase 9")


def generate_pdf(payload: dict, output_path: str) -> str:
    """
    Render report payload to PDF using WeasyPrint.

    Args:
        payload: Report payload from build_report_payload().
        output_path: File path to write PDF.

    Returns:
        Absolute path to generated PDF file.
    """
    raise NotImplementedError("Phase 9")
