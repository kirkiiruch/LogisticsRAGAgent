"""Local configuration persistence for LogisticsRAGAgent (%APPDATA%\\LogisticsRAGAgent\\config.json)."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from i18n import DEFAULT_LANGUAGE, normalize_language

APP_DIR_NAME = "LogisticsRAGAgent"
CONFIG_FILE_NAME = "config.json"

DEFAULT_CHAT_WEBHOOK_URL = "http://localhost:5678/webhook/logistics-agent"
DEFAULT_INGEST_WEBHOOK_URL = "http://localhost:5678/webhook/rag-ingest"
DEFAULT_TIMEOUT_SECONDS = 90
MIN_TIMEOUT_SECONDS = 5
VALID_APPEARANCE_MODES = ("System", "Dark", "Light")


def get_appdata_root(appdata_dir: str | Path | None = None) -> Path:
    """Resolve the Windows AppData Roaming directory without touching the repository."""
    if appdata_dir is not None:
        return Path(appdata_dir)
    env_appdata = os.environ.get("APPDATA", "").strip()
    if env_appdata:
        return Path(env_appdata)
    return Path.home() / "AppData" / "Roaming"


def get_default_config_path(appdata_dir: str | Path | None = None) -> Path:
    """Return the canonical config path under %APPDATA%\\LogisticsRAGAgent\\config.json."""
    return get_appdata_root(appdata_dir) / APP_DIR_NAME / CONFIG_FILE_NAME


def _normalize_appearance_mode(mode: str | None) -> str:
    if not mode:
        return "System"
    cleaned = str(mode).strip().capitalize()
    if cleaned in VALID_APPEARANCE_MODES:
        return cleaned
    return "System"


def _normalize_timeout(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_SECONDS
    return max(MIN_TIMEOUT_SECONDS, parsed)


@dataclass
class AppConfig:
    """Strongly-typed runtime configuration persisted in AppData."""

    language: str = DEFAULT_LANGUAGE
    chat_webhook_url: str = DEFAULT_CHAT_WEBHOOK_URL
    ingest_webhook_url: str = DEFAULT_INGEST_WEBHOOK_URL
    bearer_token: str = ""
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    session_id: str = ""
    appearance_mode: str = "System"

    def __post_init__(self) -> None:
        self.language = normalize_language(self.language)
        self.chat_webhook_url = (
            str(self.chat_webhook_url or DEFAULT_CHAT_WEBHOOK_URL).strip()
            or DEFAULT_CHAT_WEBHOOK_URL
        )
        self.ingest_webhook_url = (
            str(self.ingest_webhook_url or DEFAULT_INGEST_WEBHOOK_URL).strip()
            or DEFAULT_INGEST_WEBHOOK_URL
        )
        self.bearer_token = str(self.bearer_token or "").strip()
        self.timeout_seconds = _normalize_timeout(self.timeout_seconds)
        self.session_id = str(self.session_id or "").strip() or str(uuid.uuid4())
        self.appearance_mode = _normalize_appearance_mode(self.appearance_mode)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfigManager:
    """Loads and saves LogisticsRAGAgent settings strictly in %APPDATA%."""

    def __init__(
        self,
        config_path: str | Path | None = None,
        appdata_dir: str | Path | None = None,
    ) -> None:
        if config_path is not None:
            self.config_path = Path(config_path)
        else:
            self.config_path = get_default_config_path(appdata_dir=appdata_dir)
        self.config: AppConfig = self.load()

    def load(self) -> AppConfig:
        """Load configuration from disk or create defaults with a persisted session_id."""
        if self.config_path.exists():
            try:
                raw_text = self.config_path.read_text(encoding="utf-8")
                data = json.loads(raw_text)
                if isinstance(data, dict):
                    loaded = AppConfig(
                        language=data.get("language", DEFAULT_LANGUAGE),
                        chat_webhook_url=data.get(
                            "chat_webhook_url", DEFAULT_CHAT_WEBHOOK_URL
                        ),
                        ingest_webhook_url=data.get(
                            "ingest_webhook_url", DEFAULT_INGEST_WEBHOOK_URL
                        ),
                        bearer_token=data.get("bearer_token", ""),
                        timeout_seconds=data.get(
                            "timeout_seconds", DEFAULT_TIMEOUT_SECONDS
                        ),
                        session_id=data.get("session_id", ""),
                        appearance_mode=data.get("appearance_mode", "System"),
                    )
                    if not data.get("session_id"):
                        self.save(loaded)
                    self.config = loaded
                    return loaded
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass

        default_cfg = AppConfig()
        self.save(default_cfg)
        self.config = default_cfg
        return default_cfg

    def save(self, config: AppConfig | None = None) -> Path:
        """Persist configuration to disk as UTF-8 JSON."""
        target = config if config is not None else self.config
        normalized = AppConfig(**target.to_dict())
        self.config = normalized
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(normalized.to_dict(), indent=2, ensure_ascii=False)
        self.config_path.write_text(payload + "\n", encoding="utf-8")
        return self.config_path

    def update(self, **kwargs: Any) -> AppConfig:
        """Update specific config fields and immediately save to disk."""
        current = self.config.to_dict()
        current.update(kwargs)
        updated = AppConfig(**current)
        self.save(updated)
        return self.config

    def reset_session_id(self) -> str:
        """Generate and persist a fresh UUID4 session_id for a new conversation."""
        new_id = str(uuid.uuid4())
        self.update(session_id=new_id)
        return new_id