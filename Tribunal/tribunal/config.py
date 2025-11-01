"""Configuration helpers for the Tribunal application."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


def _as_bool(name: str, default: bool) -> bool:
    """Parse environment variables into booleans."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _split_words(value: str) -> tuple[str, ...]:
    return tuple(filter(None, (part.strip() for part in value.split(","))))


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the Tribunal application."""

    secret_key: str = os.getenv("TRIBUNAL_SECRET_KEY", "change-me")
    flask_host: str = os.getenv("TRIBUNAL_FLASK_HOST", "127.0.0.1")
    flask_port: int = int(os.getenv("TRIBUNAL_FLASK_PORT", "5002"))
    ipfs_api_addr: str = os.getenv("TRIBUNAL_IPFS_API", "/ip4/127.0.0.1/tcp/5001")
    ipfs_binary: str = os.getenv("TRIBUNAL_IPFS_BINARY", "ipfs")
    ipfs_enabled: bool = field(default_factory=lambda: _as_bool("TRIBUNAL_IPFS_ENABLED", True))
    auto_start_ipfs_daemon: bool = field(default_factory=lambda: _as_bool("TRIBUNAL_IPFS_AUTOSTART", True))
    enable_pubsub_listener: bool = field(default_factory=lambda: _as_bool("TRIBUNAL_ENABLE_PUBSUB", True))
    pubsub_topic: str = os.getenv("TRIBUNAL_PUBSUB_TOPIC", "conflictos-app")
    forbidden_words: tuple[str, ...] = field(
        default_factory=lambda: _split_words(os.getenv("TRIBUNAL_FORBIDDEN_WORDS", "insulto1,insulto2"))
    )
    async_mode: str = os.getenv("TRIBUNAL_SOCKETIO_ASYNC_MODE", "threading")
    socketio_cors: str | None = os.getenv("TRIBUNAL_SOCKETIO_CORS")
    state_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "TRIBUNAL_STATE_DIR",
                Path(__file__).resolve().parent.parent / "var",
            )
        )
    )
    cid_filename: str = os.getenv("TRIBUNAL_CID_FILENAME", "current_cid.txt")
    local_backup_filename: str = os.getenv("TRIBUNAL_LOCAL_BACKUP", "data.json")

    def __post_init__(self) -> None:
        self.state_dir = Path(self.state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.forbidden_words:
            self.forbidden_words = ("insulto1", "insulto2")

    @property
    def current_cid_path(self) -> Path:
        return self.state_dir / self.cid_filename

    @property
    def local_backup_path(self) -> Path:
        return self.state_dir / self.local_backup_filename
