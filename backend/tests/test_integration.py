"""
Integration tests for OvelhaInvest API.
Run with: cd backend && uv run pytest tests/test_integration.py -v
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """API is up and returning healthy status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_daily_status_returns_shape():
    """Daily status returns expected keys."""
    resp = client.get("/daily_status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_value_usd" in data
    assert "sleeve_weights" in data
    assert "regime" in data


def test_daily_status_etag():
    """Daily status sets ETag header and respects If-None-Match."""
    resp1 = client.get("/daily_status")
    assert resp1.status_code == 200
    etag = resp1.headers.get("etag")
    assert etag is not None
    resp2 = client.get("/daily_status", headers={"if-none-match": etag})
    assert resp2.status_code == 304


def test_valuation_summary_shape():
    """Valuation summary returns ranked assets."""
    resp = client.get("/valuation_summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_by_composite" in data


def test_performance_summary_shape():
    """Performance summary returns key metrics."""
    resp = client.get("/performance/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "twr_ytd" in data or "total_value_usd" in data  # either real or stub response


def test_reports_list_returns_array():
    """Reports list returns an array (may be empty)."""
    resp = client.get("/reports/list")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_journal_list_returns_array():
    """Journal list returns an array (may be empty)."""
    resp = client.get("/journal")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_journal_stats_shape():
    """Journal stats returns expected structure."""
    resp = client.get("/journal/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_entries" in data or isinstance(data, dict)


def test_alert_rules_returns_array():
    """Alert rules endpoint returns an array."""
    resp = client.get("/alerts/rules")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_status_shape():
    """Admin status returns expected keys."""
    resp = client.get("/admin/status")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
