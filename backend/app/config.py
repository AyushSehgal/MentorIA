"""Runtime settings loaded from environment / .env (never commit .env)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
FIXTURES_DIR = REPO_ROOT / "fixtures"
load_dotenv(REPO_ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str, default: str) -> Path:
    raw = os.getenv(name) or default
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / p


@dataclass
class Settings:
    demo_mode: bool
    timezone: str
    db_path: Path
    upload_dir: Path
    synthetic_file: Path
    llm_enabled: bool
    llm_model: str
    canvas_base_url: str
    canvas_token: str
    google_client_id: str
    google_client_secret: str
    google_token_file: Path
    google_calendar_write_enabled: bool
    piazza_enabled: bool
    piazza_email: str
    piazza_password: str
    piazza_network_ids: list[str]

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def load_settings() -> Settings:
    db_path = _path("NOVA_DB_PATH", "backend/data/nova.db")
    return Settings(
        demo_mode=_bool("DEMO_MODE", True),
        timezone=os.getenv("NOVA_TIMEZONE", "America/New_York"),
        db_path=db_path,
        upload_dir=_path("NOVA_UPLOAD_DIR", str(db_path.parent / "uploads")),
        synthetic_file=_path("NOVA_SYNTHETIC_FILE", "fixtures/synthetic_world.md"),
        llm_enabled=_bool("LLM_ENABLED", False),
        llm_model=os.getenv("LLM_MODEL", "claude-opus-5-5"),
        canvas_base_url=os.getenv("CANVAS_BASE_URL", "").rstrip("/"),
        canvas_token=os.getenv("CANVAS_API_TOKEN", ""),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        google_token_file=_path("GOOGLE_TOKEN_FILE", "backend/data/google_token.json"),
        google_calendar_write_enabled=_bool("GOOGLE_CALENDAR_WRITE_ENABLED", False),
        piazza_enabled=_bool("PIAZZA_ENABLED", False),
        piazza_email=os.getenv("PIAZZA_EMAIL", ""),
        piazza_password=os.getenv("PIAZZA_PASSWORD", ""),
        piazza_network_ids=[x for x in os.getenv("PIAZZA_NETWORK_IDS", "").split(",") if x],
    )


settings = load_settings()


def reload_settings() -> Settings:
    global settings
    new = load_settings()
    settings.__dict__.update(new.__dict__)
    return settings
