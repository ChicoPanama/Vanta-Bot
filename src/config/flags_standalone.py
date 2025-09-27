import os

def _get_env(name: str, default: str = "DRY") -> str:
    return os.getenv(name, default)

def execution_mode() -> str:
    return _get_env("COPY_EXECUTION_MODE", "DRY")  # "DRY" or "LIVE"

def is_live() -> bool:
    return execution_mode().upper() == "LIVE"
