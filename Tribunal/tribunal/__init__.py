"""Application factory for the Tribunal project."""

from __future__ import annotations

from pathlib import Path
import logging

from flask import Flask

from .config import Settings
from .data_store import DataRepository
from .routes import bp as web_blueprint
from .sockets import init_socketio, socketio


LOGGER = logging.getLogger(__name__)
PACKAGE_ROOT = Path(__file__).resolve().parent


def create_application(settings: Settings | None = None):
    """Create and configure the Flask/Socket.IO application."""

    settings = settings or Settings()
    templates_dir = PACKAGE_ROOT.parent / "templates"
    static_dir = PACKAGE_ROOT.parent / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir),
    )
    app.config.update(
        SECRET_KEY=settings.secret_key,
        FORBIDDEN_WORDS=settings.forbidden_words,
    )

    repository = DataRepository(settings)
    app.config["DATA_REPOSITORY"] = repository

    app.register_blueprint(web_blueprint)

    init_socketio(settings.async_mode, settings.socketio_cors)
    socketio.init_app(app, async_mode=settings.async_mode, cors_allowed_origins=settings.socketio_cors)

    if settings.enable_pubsub_listener:
        LOGGER.info("Activando listener de PubSub de IPFS")

        def _on_new_cid(cid: str) -> None:
            socketio.emit("data_updated", {"cid": cid})

        repository.start_pubsub_listener(_on_new_cid)

    return app, socketio


__all__ = ["create_application", "Settings", "socketio"]
