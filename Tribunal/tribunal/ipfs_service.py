"""Utilities to manage connections and interactions with an IPFS daemon."""

from __future__ import annotations

from pathlib import Path
import logging
import subprocess
import sys
import threading
import time
from typing import Callable, Optional

from .config import Settings

try:  # pragma: no cover - optional dependency during tests
    import ipfshttpclient  # type: ignore
except Exception:  # pragma: no cover - handled gracefully
    ipfshttpclient = None


LOGGER = logging.getLogger(__name__)


class IPFSUnavailable(RuntimeError):
    """Raised when IPFS cannot be used."""


class IPFSService:
    """Lazy IPFS client manager with optional daemon auto-start."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client_lock = threading.RLock()
        self._client: Optional["ipfshttpclient.Client"] = None
        self._daemon_process: Optional[subprocess.Popen[str]] = None

    @property
    def enabled(self) -> bool:
        return bool(self._settings.ipfs_enabled and ipfshttpclient is not None)

    def ensure_client(self) -> "ipfshttpclient.Client":
        if not self.enabled:
            raise IPFSUnavailable("IPFS support is disabled or ipfshttpclient is not installed.")
        with self._client_lock:
            if self._client is None:
                self._ensure_daemon_running()
                self._client = ipfshttpclient.connect(self._settings.ipfs_api_addr)
            return self._client

    # ------------------------------------------------------------------
    # Daemon helpers
    # ------------------------------------------------------------------
    def _ensure_daemon_running(self) -> None:
        if self._is_daemon_running():
            return
        if not self._settings.auto_start_ipfs_daemon:
            raise IPFSUnavailable("IPFS daemon is not running and auto-start is disabled.")
        self._start_daemon()
        for _ in range(60):
            time.sleep(1)
            if self._is_daemon_running():
                return
        raise IPFSUnavailable("IPFS daemon did not become ready in time.")

    def _start_daemon(self) -> None:
        binary = self._resolve_binary()
        LOGGER.info("Starting IPFS daemon using %s", binary)
        try:
            self._daemon_process = subprocess.Popen(  # noqa: S603
                [binary, "daemon", "--enable-pubsub-experiment"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:  # pragma: no cover - subprocess failure is environment dependent
            raise IPFSUnavailable(f"Could not start IPFS daemon: {exc}") from exc

    def _resolve_binary(self) -> str:
        binary = self._settings.ipfs_binary
        if getattr(sys, "frozen", False):  # Support PyInstaller bundles
            base_path = Path(getattr(sys, "_MEIPASS"))
            binary = str(base_path / binary)
        return binary

    def _is_daemon_running(self) -> bool:
        if not self.enabled:
            return False
        try:
            with ipfshttpclient.connect(self._settings.ipfs_api_addr) as client:
                client.id()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public APIs used by the data repository
    # ------------------------------------------------------------------
    def add_json(self, payload: dict) -> str:
        client = self.ensure_client()
        return client.add_json(payload)

    def cat(self, cid: str) -> bytes:
        client = self.ensure_client()
        return client.cat(cid)

    def publish(self, topic: str, message: str) -> None:
        client = self.ensure_client()
        client.pubsub.publish(topic, message)

    def subscribe(self, topic: str, callback: Callable[[str], None]) -> threading.Thread:
        client = self.ensure_client()

        def _runner() -> None:
            try:
                for message in client.pubsub.subscribe(topic):
                    data = message.get("data", b"")
                    if isinstance(data, bytes):
                        callback(data.decode("utf-8"))
                    else:
                        callback(str(data))
            except Exception as exc:  # pragma: no cover - external dependency behaviour
                LOGGER.warning("IPFS pubsub listener stopped: %s", exc)

        listener = threading.Thread(target=_runner, daemon=True)
        listener.start()
        return listener
