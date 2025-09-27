from src.config.settings_new import settings

def execution_mode() -> str:
    return settings.copy_execution_mode  # "DRY" or "LIVE"

def is_live() -> bool:
    return execution_mode().upper() == "LIVE"
