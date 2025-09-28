"""Configuration package exports."""

try:  # pragma: no cover - allows importing config without installed dependencies
    from .settings import Settings, config, get_settings, settings
except Exception:  # noqa: BLE001
    Settings = None  # type: ignore
    settings = None  # type: ignore
    config = None  # type: ignore
    get_settings = None  # type: ignore

__all__ = ["Settings", "settings", "config", "get_settings"]
