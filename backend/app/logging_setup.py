"""Rotating file log: logs/app.log, 5 files x 1 MB. Resume text is never logged."""
import logging
from logging.handlers import RotatingFileHandler

from .config import settings


def setup_logging() -> None:
    root = logging.getLogger("hiretrack")
    if root.handlers:
        return
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        settings.log_dir / "app.log", maxBytes=1_000_000, backupCount=4, encoding="utf-8"
    )  # app.log + 4 rotated files = 5 files
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(console)
    root.setLevel(settings.log_level)
    root.propagate = False
