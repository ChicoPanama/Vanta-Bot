"""Tests for structured logging (Phase 8)."""

import io
import json
import sys

from src.monitoring.logging import log


class TestLogging:
    def test_log_shape(self, monkeypatch) -> None:
        """Test log outputs valid JSON."""
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stdout", buf)
        log("info", "test message", foo="bar")
        output = buf.getvalue().strip()
        j = json.loads(output)
        assert j["level"] == "INFO"
        assert j["msg"] == "test message"
        assert j["foo"] == "bar"
        assert "ts" in j
        assert "component" in j
