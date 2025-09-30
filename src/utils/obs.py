"""Observability helpers (logging, Sentry integration, correlation IDs)."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
ENV = os.getenv("ENV", "local")

try:  # pragma: no cover - best-effort optional dependency
    import sentry_sdk

    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN, traces_sample_rate=float(os.getenv("SENTRY_TRACES", "0.0"))
        )
        SENTRY_ENABLED = True
    else:
        SENTRY_ENABLED = False
except Exception as exc:  # noqa: BLE001
    logger.warning("Failed to initialise Sentry SDK", exc_info=exc)
    SENTRY_ENABLED = False


class JsonFormatter(logging.Formatter):
    """Emit logs as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - overriding
        payload: dict[str, Any] = {
            "lvl": record.levelname,
            "msg": record.getMessage(),
            "ts": int(time.time() * 1000),
            "logger": record.name,
            "env": ENV,
        }
        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in reserved:
                continue
            payload[key] = value
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_json_logging(level: str = "INFO") -> None:
    """Configure root logger for JSON-formatted stdout output."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def rid() -> str:
    """Return a short correlation identifier."""
    return uuid.uuid4().hex[:12]


def log_exc(exc: Exception, context: dict[str, Any] | None = None) -> None:
    """Log *exc* and forward to Sentry when available."""
    data: dict[str, Any]
    if context is None:
        data = {}
    elif isinstance(context, dict):
        data = dict(context)
    else:
        data = {"context": str(context)}
    enriched = {"err": str(exc), **data}
    logger.error("error", extra=enriched, exc_info=exc)
    if SENTRY_ENABLED:
        try:  # pragma: no cover - depends on sentry_sdk
            import sentry_sdk

            sentry_sdk.capture_exception(exc)
        except Exception as sentry_error:  # noqa: BLE001
            logger.warning("Failed to send error to Sentry", exc_info=sentry_error)


__all__ = ["JsonFormatter", "setup_json_logging", "rid", "log_exc", "SENTRY_ENABLED"]
