"""Data persistence helpers backed by JSON storage."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import logging
import threading
from typing import Any, Dict, Optional

from .config import Settings


LOGGER = logging.getLogger(__name__)


DEFAULT_DATA: Dict[str, Any] = {
    "usuarios": [],
    "conflictos": [],
    "votos": [],
    "comentarios": {},
}


class DataRepository:
    """Centralised access to application data."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.RLock()
        self._ensure_storage_exists()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def load_data(self) -> Dict[str, Any]:
        with self._lock:
            payload = self._load_from_disk()
            return self._ensure_schema(payload)

    def save_data(self, data: Dict[str, Any]) -> None:
        with self._lock:
            materialised = self._ensure_schema(data)
            self._write_to_disk(materialised)

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
    def _ensure_storage_exists(self) -> None:
        if not self._settings.data_path.exists():
            self._write_to_disk(deepcopy(DEFAULT_DATA))

    def _load_from_disk(self) -> Dict[str, Any]:
        try:
            return json.loads(self._settings.data_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            LOGGER.info("Storage file not found, rebuilding from defaults")
            self._write_to_disk(deepcopy(DEFAULT_DATA))
            return deepcopy(DEFAULT_DATA)
        except json.JSONDecodeError as exc:
            LOGGER.warning("Corrupt data file detected, resetting storage: %s", exc)
            self._write_to_disk(deepcopy(DEFAULT_DATA))
            return deepcopy(DEFAULT_DATA)

    def _write_to_disk(self, data: Dict[str, Any]) -> None:
        try:
            self._settings.data_path.write_text(
                json.dumps(data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - IO failure
            LOGGER.error("Unable to write data file: %s", exc)

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
