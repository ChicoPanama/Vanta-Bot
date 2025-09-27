from __future__ import annotations
import json, logging, os, time, uuid
from typing import Any, Dict, Optional

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
ENV = os.getenv("ENV", "local")

try:
    import sentry_sdk
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=float(os.getenv("SENTRY_TRACES", "0.0")))
        SENTRY = True
    else:
        SENTRY = False
except Exception:
    SENTRY = False

class JsonFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "lvl": record.levelname,
            "msg": record.getMessage(),
            "ts": int(time.time() * 1000),
            "logger": record.name,
            "env": ENV,
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            base.update(record.extra)
        return json.dumps(base, ensure_ascii=False)

def setup_json_logging(level: str = "INFO"):
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(h)
    root.setLevel(level)

def rid() -> str:
    return uuid.uuid4().hex[:12]

def log_exc(e: Exception, context: Optional[Dict[str, Any]] = None):
    logging.getLogger("vanta.obs").error("error", extra={"extra": {"err": str(e), **(context or {})}})
    if SENTRY:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
