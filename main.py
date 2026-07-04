"""Entry point for sorting-tray."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from sorting_tray.applog import get_logger, log_path, setup_logging
from sorting_tray.fonts import load_fonts
from sorting_tray.mainwindow import MainWindow


def main() -> int:
    setup_logging(Path(__file__).resolve().parent)
    log = get_logger("startup")
    app = QApplication(sys.argv)
    app.setApplicationName("sorting-tray")
    # Register the bundled industrial-redesign fonts before any widget is styled.
    load_fonts()
    try:
        window = MainWindow()
        window.showMaximized()
        log.info("window shown; entering event loop")
        return app.exec()
    except Exception:
        log.critical("fatal error during startup", exc_info=True)
        raise
    finally:
        log.info("event loop exited (log at %s)", log_path())


if __name__ == "__main__":
    sys.exit(main())
