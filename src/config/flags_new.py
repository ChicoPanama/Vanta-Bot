from src.config.settings import settings


def execution_mode() -> str:
    return settings.COPY_EXECUTION_MODE  # "DRY" or "LIVE"


def is_live() -> bool:
    return settings.is_live_mode()
