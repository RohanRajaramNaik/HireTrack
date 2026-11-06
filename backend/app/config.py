"""Application configuration.

All paths are resolved relative to the project root so the app behaves the same
no matter which directory uvicorn is started from.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")

# Run fully offline once the model has been downloaded. download_model.py
# overrides this for the one-off download.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


class Settings:
    data_dir: Path = Path(os.getenv("HIRETRACK_DATA_DIR", PROJECT_ROOT / "data"))
    backup_dir: Path = Path(os.getenv("HIRETRACK_BACKUP_DIR", PROJECT_ROOT / "backups"))
    log_dir: Path = Path(os.getenv("HIRETRACK_LOG_DIR", PROJECT_ROOT / "logs"))
    model_dir: Path = Path(os.getenv("HIRETRACK_MODEL_DIR", PROJECT_ROOT / "models"))
    frontend_dist: Path = PROJECT_ROOT / "frontend" / "dist"
    seed_dir: Path = BACKEND_DIR / "seed"

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    admin_passcode_hash: str = os.getenv("ADMIN_PASSCODE_HASH", "")

    # Disable the semantic model (e.g. in fast unit tests). A deterministic
    # hashing fallback is used instead so the app still works.
    disable_model: bool = os.getenv("HIRETRACK_DISABLE_MODEL", "0") == "1"
    # Skip the automatic start-up backup (tests).
    disable_startup_backup: bool = os.getenv("HIRETRACK_DISABLE_STARTUP_BACKUP", "0") == "1"

    cors_origins: list[str] = [
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    max_backups: int = 10

    @property
    def db_path(self) -> Path:
        return self.data_dir / "hiretrack.db"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.backup_dir, self.log_dir):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
