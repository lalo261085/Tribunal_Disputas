"""Convenience script to run the Tribunal web server."""

from __future__ import annotations

import logging

from tribunal import Settings, create_application


def main() -> None:
    settings = Settings()
    app, socketio = create_application(settings)
    logging.basicConfig(level=logging.INFO)
    socketio.run(
        app,
        host=settings.flask_host,
        port=settings.flask_port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry
    main()
