"""Desktop entry point using PyQt5."""

from __future__ import annotations

import logging
import sys
import threading

from .config import Settings
from . import create_application


LOGGER = logging.getLogger(__name__)


def run_desktop_app(settings: Settings | None = None) -> None:
    """Start the Flask app and embed it inside a PyQt web view."""

    settings = settings or Settings()
    flask_app, socketio = create_application(settings)

    def _run_flask() -> None:
        LOGGER.info("Iniciando servidor Flask en %s:%s", settings.flask_host, settings.flask_port)
        socketio.run(
            flask_app,
            host=settings.flask_host,
            port=settings.flask_port,
            debug=False,
            use_reloader=False,
        )

    flask_thread = threading.Thread(target=_run_flask, daemon=True)
    flask_thread.start()

    try:
        from PyQt5.QtCore import QUrl
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtWidgets import QApplication, QMainWindow
    except Exception as exc:  # pragma: no cover - optional UI dependency
        raise RuntimeError("PyQt5 no est? disponible en el entorno actual") from exc

    class MainWindow(QMainWindow):  # pragma: no cover - requires UI environment
        def __init__(self) -> None:
            super().__init__()
            self.browser = QWebEngineView()
            self.setCentralWidget(self.browser)
            url = QUrl(f"http://{settings.flask_host}:{settings.flask_port}")
            self.browser.setUrl(url)
            self.setWindowTitle("Tribunal")
            self.showMaximized()

    qt_app = QApplication(sys.argv)
    window = MainWindow()  # Mantener referencia para evitar GC prematuro
    sys.exit(qt_app.exec_())
