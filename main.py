"""
Customer Manager - application entry point.

Run with:  python main.py
Build a Windows .exe with: see build/README_BUILD.md
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.utils.logging_setup import configure_logging
from app.utils.error_handling import install_global_exception_hook
from app.utils.paths import resource_path
from app.database.init_db import initialize_database
from app.database.migrations import run_migrations
from app.database.engine import shutdown_database
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


class AppController:
    """Owns the login <-> main window transition."""

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.login_window: LoginWindow | None = None
        self.main_window: MainWindow | None = None
        self._show_login()

    def _show_login(self) -> None:
        self.main_window = None
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self._on_login_successful)
        self.login_window.show()

    def _on_login_successful(self, must_change_password: bool) -> None:
        if self.login_window:
            self.login_window.close()
            self.login_window = None

        self.main_window = MainWindow()
        self.main_window._on_logout_requested = self._show_login  # wire logout back to login screen
        self.main_window.show()

        if must_change_password:
            self.main_window.prompt_change_password(forced=True)


def main() -> None:
    configure_logging()
    logger.info("Application starting.")

    app = QApplication(sys.argv)
    app.setApplicationName("Customer Manager")

    install_global_exception_hook()

    try:
        initialize_database()
        run_migrations()
    except Exception as e:
        logger.exception("Fatal error during database initialization.")
        # This can happen before the Qt event loop starts, so show the error
        # directly rather than relying on the global exception hook - a
        # startup failure must never be silent, especially for a windowed
        # (no console) build where a silent crash would look exactly like
        # "the app just doesn't open."
        QMessageBox.critical(
            None,
            "Unable to Start",
            "The application could not start because its data could not be "
            "opened.\n\n"
            f"Details: {e}\n\n"
            "Your data has not been deleted. If you continue to see this, "
            "please check the backups folder for a recent backup, or get "
            "help before making any further changes.",
        )
        sys.exit(1)

    style_path = resource_path("resources/style.qss")
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))

    controller = AppController(app)  # noqa: F841 - keep alive for the app lifetime

    app.aboutToQuit.connect(shutdown_database)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
