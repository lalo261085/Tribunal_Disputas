"""Configuration helpers for the Tribunal application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


def _split_words(value: str) -> tuple[str, ...]:
    return tuple(filter(None, (part.strip() for part in value.split(","))))


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the Tribunal application."""

    secret_key: str = os.getenv("TRIBUNAL_SECRET_KEY", "change-me")
    flask_host: str = os.getenv("TRIBUNAL_FLASK_HOST", "127.0.0.1")
    flask_port: int = int(os.getenv("TRIBUNAL_FLASK_PORT", "5002"))
    data_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "TRIBUNAL_DATA_DIR",
                Path(__file__).resolve().parent.parent / "var",
            )
        )
    )
    data_filename: str = os.getenv("TRIBUNAL_DATA_FILE", "disputes.json")
    api_token: str | None = os.getenv("TRIBUNAL_API_TOKEN")
    forbidden_words: tuple[str, ...] = field(
        default_factory=lambda: _split_words(os.getenv("TRIBUNAL_FORBIDDEN_WORDS", "insulto1,insulto2"))
    )

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.forbidden_words:
            self.forbidden_words = ("insulto1", "insulto2")
        if self.api_token:
            token = self.api_token.strip()
            self.api_token = token or None

    @property
    def data_path(self) -> Path:
        return self.data_dir / self.data_filename
