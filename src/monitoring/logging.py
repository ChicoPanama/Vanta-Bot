"""Structured JSON logging (Phase 8)."""

import json
import os
import sys
import time
import uuid
from typing import Any

COMPONENT = os.environ.get("COMPONENT", "app")


def log(level: str, msg: str, **kv: Any):
    """Emit structured JSON log.

    Args:
        level: Log level (info, warn, error)
        msg: Log message
        **kv: Additional key-value pairs
    """
    payload = {
        "ts": round(time.time(), 3),
        "level": level.upper(),
        "component": COMPONENT,
        "msg": msg,
        **kv,
    }
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def with_correlation(fn):
    """Decorator to add correlation ID to function calls.

    Args:
        fn: Function to wrap

    Returns:
        Wrapped function with correlation_id
    """

    def wrap(*args, **kwargs):
        cid = kwargs.get("correlation_id") or str(uuid.uuid4())
        try:
            return fn(*args, correlation_id=cid, **kwargs)
        except Exception as e:
            log("error", "unhandled", correlation_id=cid, error=str(e))
            raise

    return wrap
