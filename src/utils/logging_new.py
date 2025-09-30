import json
import logging
import sys

from src.config.settings import settings


def setup_logging(service: str = "vanta-bot") -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    class _Fmt(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            if settings.log_json:
                return json.dumps(
                    {
                        "lvl": record.levelname,
                        "svc": service,
                        "msg": record.getMessage(),
                    }
                )
            return f"[{record.levelname}] {service} {record.getMessage()}"

    handler.setFormatter(_Fmt())
    root.handlers = [handler]
