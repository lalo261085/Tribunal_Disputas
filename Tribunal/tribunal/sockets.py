"""Socket.IO configuration and event handlers."""

from __future__ import annotations

import logging

from flask import current_app
from flask_socketio import SocketIO, emit


LOGGER = logging.getLogger(__name__)

socketio = SocketIO()


def init_socketio(async_mode: str = "threading", cors_allowed_origins: str | None = None) -> SocketIO:
    socketio.async_mode = async_mode
    if cors_allowed_origins:
        socketio.cors_allowed_origins = cors_allowed_origins
    register_handlers()
    return socketio


def register_handlers() -> None:
    @socketio.on("connect")
    def handle_connect():  # pragma: no cover - exercised at runtime
        LOGGER.info("Cliente conectado")

    @socketio.on("signal")
    def handle_signal(data):  # pragma: no cover - exercised at runtime
        emit("signal", data, broadcast=True)
        if current_app:
            current_app.logger.debug("Signal reenviado a clientes")
