"""API webhook health check tests (Phase 6)."""

from fastapi.testclient import TestClient

from src.api.webhook import app


class TestWebhookHealth:
    """Test webhook API health endpoint."""

    def test_health(self) -> None:
        """Test health endpoint returns ok."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "vanta-bot-signals"}
