"""Settings read from the repository-root `.env` (see handoff/.env.example).

Paths in `.env` such as the SQLite file are resolved against the repository
root, so the backend behaves the same no matter which directory it starts in.
Real environment variables win over `.env` values (override=False).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = REPO_ROOT / "handoff"
CONTRACTS_DIR = HANDOFF_DIR / "contracts"
FIXTURES_DIR = HANDOFF_DIR / "fixtures"
PROMPTS_FILE = HANDOFF_DIR / "prompts" / "stage_prompts.md"

load_dotenv(REPO_ROOT / ".env", override=False)


def _float_or_none(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


def _resolve_sqlite_url(url: str) -> str:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError("DATABASE_URL must be a sqlite:/// URL")
    raw = url[len(prefix):]
    path = Path(raw)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return prefix + str(path)


@dataclass
class Settings:
    app_mode: str
    database_url: str
    backend_host: str
    backend_port: int
    frontend_origin: str
    anthropic_api_key: str
    anthropic_workspace_id: str
    llm_model: str
    llm_timeout_seconds: float
    llm_max_output_tokens: int
    llm_input_usd_per_million: float | None
    llm_output_usd_per_million: float | None
    demo_stage_delay_seconds: float

    @property
    def live_configured(self) -> bool:
        return bool(self.anthropic_api_key and self.llm_model)

    @property
    def sqlite_path(self) -> Path:
        return Path(self.database_url[len("sqlite:///"):])


def load_settings() -> Settings:
    mode = os.getenv("APP_MODE", "demo").strip() or "demo"
    if mode not in ("demo", "live"):
        raise ValueError("APP_MODE must be demo or live")
    return Settings(
        app_mode=mode,
        database_url=_resolve_sqlite_url(os.getenv("DATABASE_URL", "sqlite:///./data/prototype.db")),
        backend_host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        backend_port=int(os.getenv("BACKEND_PORT", "8000")),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:3000"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_workspace_id=os.getenv("ANTHROPIC_WORKSPACE_ID", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "").strip(),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60") or 60),
        llm_max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "8192") or 8192),
        llm_input_usd_per_million=_float_or_none(os.getenv("LLM_INPUT_USD_PER_MILLION")),
        llm_output_usd_per_million=_float_or_none(os.getenv("LLM_OUTPUT_USD_PER_MILLION")),
        # Not in .env.example: a short pause so the demo shows the polling state.
        demo_stage_delay_seconds=float(os.getenv("DEMO_STAGE_DELAY_SECONDS", "1.0") or 0),
    )


settings = load_settings()
