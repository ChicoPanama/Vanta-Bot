"""Tests for Prometheus metrics (Phase 8)."""

from fastapi.testclient import TestClient

from src.api.webhook import app


class TestMetrics:
    def test_metrics_endpoint(self) -> None:
        """Test metrics endpoint serves Prometheus format."""
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"vanta_signals_queued_total" in response.content
