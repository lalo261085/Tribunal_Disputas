"""Data persistence helpers with IPFS integration and local fallback."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import logging
import threading
from typing import Any, Dict, Optional

from .config import Settings
from .ipfs_service import IPFSService, IPFSUnavailable


LOGGER = logging.getLogger(__name__)


DEFAULT_DATA: Dict[str, Any] = {
    "usuarios": [],
    "conflictos": [],
    "votos": [],
    "comentarios": {},
}


class DataRepository:
    """Centralised access to application data."""

    def __init__(self, settings: Settings, ipfs_service: Optional[IPFSService] = None) -> None:
        self._settings = settings
        self._ipfs = ipfs_service or IPFSService(settings)
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def load_data(self) -> Dict[str, Any]:
        with self._lock:
            payload = self._load_from_ipfs() or self._load_from_local()
            return self._ensure_schema(payload)

    def save_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Persist the payload and return the resulting CID (if IPFS is enabled)."""

        with self._lock:
            materialised = self._ensure_schema(data)
            cid: Optional[str] = None
            if self._ipfs.enabled:
                try:
                    cid = self._ipfs.add_json(materialised)
                    self._write_current_cid(cid)
                    self._ipfs.publish(self._settings.pubsub_topic, cid)
                except IPFSUnavailable as exc:
                    LOGGER.warning("IPFS unavailable, falling back to local storage: %s", exc)
                except Exception as exc:  # pragma: no cover - network dependant
                    LOGGER.warning("Unable to persist data to IPFS: %s", exc)
            self._write_local_backup(materialised)
            return cid

    def start_pubsub_listener(self, on_new_cid) -> Optional[threading.Thread]:
        if not (self._ipfs.enabled and self._settings.enable_pubsub_listener):
            return None

        def _handle(cid: str) -> None:
            LOGGER.info("Received CID update from pubsub: %s", cid)
            with self._lock:
                self._write_current_cid(cid)
            on_new_cid(cid)

        try:
            return self._ipfs.subscribe(self._settings.pubsub_topic, _handle)
        except IPFSUnavailable as exc:
            LOGGER.warning("Unable to start pubsub listener: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Conflict phase helpers
    # ------------------------------------------------------------------
    def advance_conflict_phases(self, data: Dict[str, Any], current_time: Optional[datetime] = None) -> bool:
        """Update conflict stages based on stored timestamps."""

        current_time = current_time or datetime.now()
        changed = False
        for conflicto in data.get("conflictos", []):
            changed |= self._advance_conflict(conflicto, current_time)
        if changed:
            self.save_data(data)
        return changed

    @staticmethod
    def _advance_conflict(conflicto: Dict[str, Any], now: datetime) -> bool:
        etapa = conflicto.get("etapa")
        if etapa == "votacion" and conflicto.get("fin_votacion"):
            fin_votacion = datetime.strptime(conflicto["fin_votacion"], "%Y-%m-%dT%H:%M:%S")
            if fin_votacion < now:
                conflicto["etapa"] = "debate"
                inicio = now.strftime("%Y-%m-%dT%H:%M:%S")
                conflicto["inicio_debate"] = inicio
                conflicto["fin_debate"] = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S")
                return True
        if etapa == "debate" and conflicto.get("fin_debate"):
            fin_debate = datetime.strptime(conflicto["fin_debate"], "%Y-%m-%dT%H:%M:%S")
            if fin_debate < now:
                conflicto["etapa"] = "cerrado"
                return True
        return False

    # ------------------------------------------------------------------
    # Internal persistence helpers
    # ------------------------------------------------------------------
    def _load_from_ipfs(self) -> Optional[Dict[str, Any]]:
        if not self._ipfs.enabled:
            return None
        cid = self._read_current_cid()
        if not cid:
            return None
        try:
            payload = self._ipfs.cat(cid)
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            return json.loads(payload)
        except IPFSUnavailable:
            return None
        except Exception as exc:  # pragma: no cover - network dependant
            LOGGER.warning("Failed to load data from IPFS (cid=%s): %s", cid, exc)
            return None

    def _load_from_local(self) -> Dict[str, Any]:
        backup = self._settings.local_backup_path
        if backup.exists():
            try:
                return json.loads(backup.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - corrupted file
                LOGGER.warning("Invalid local backup, recreating: %s", exc)
        return deepcopy(DEFAULT_DATA)

    def _write_local_backup(self, data: Dict[str, Any]) -> None:
        try:
            self._settings.local_backup_path.write_text(
                json.dumps(data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - IO failure
            LOGGER.error("Unable to write local backup: %s", exc)

    def _read_current_cid(self) -> Optional[str]:
        path = self._settings.current_cid_path
        if path.exists():
            try:
                return path.read_text(encoding="utf-8").strip() or None
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Unable to read CID file: %s", exc)
        return None

    def _write_current_cid(self, cid: str) -> None:
        try:
            self._settings.current_cid_path.write_text(cid, encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Unable to persist current CID: %s", exc)

    @staticmethod
    def _ensure_schema(data: Dict[str, Any]) -> Dict[str, Any]:
        materialised = deepcopy(DEFAULT_DATA)
        for key, value in data.items():
            materialised[key] = deepcopy(value)
        # Normalise comentarios dictionary to use str keys
        materialised["comentarios"] = {
            str(key): value
            for key, value in materialised.get("comentarios", {}).items()
        }
        return materialised
