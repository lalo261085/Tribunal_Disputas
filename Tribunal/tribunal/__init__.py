"""Application factory for the Tribunal project."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import Settings
from .data_store import DataRepository
from .routes import web_bp
from .api import api_bp


PACKAGE_ROOT = Path(__file__).resolve().parent


def create_application(settings: Settings | None = None) -> Flask:
    """Create and configure the Flask application."""

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
    app.config.setdefault("VOTING_WINDOW_HOURS", 24)
    app.config["API_TOKEN"] = settings.api_token

    repository = DataRepository(settings)
    app.config["DATA_REPOSITORY"] = repository
    app.config["SETTINGS"] = settings

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


__all__ = ["create_application", "Settings"]
