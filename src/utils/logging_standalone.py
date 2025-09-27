import logging, json, sys
import os

def _get_env(name: str, default: str = "false") -> str:
    return os.getenv(name, default)

def setup_logging(service: str = "vanta-bot") -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    class _Fmt(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_json = _get_env("LOG_JSON", "false").lower() == "true"
            if log_json:
                return json.dumps({
                    "lvl": record.levelname,
                    "svc": service,
                    "msg": record.getMessage(),
                })
            return f"[{record.levelname}] {service} {record.getMessage()}"

    handler.setFormatter(_Fmt())
    root.handlers = [handler]
