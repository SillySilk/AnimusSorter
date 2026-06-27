"""File-based logging + crash tracing.

Writes a timestamped trace to <project>/logs/sorting_tray.log, mirrors it to the
console, captures uncaught exceptions (which PyQt would otherwise swallow or use
to abort), and routes Qt's own warnings into the same file. Interaction seams
(clicks, drags, drops, moves) log at DEBUG so a dead interaction can be traced
to the exact handler that did or didn't fire.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QtMsgType, qInstallMessageHandler

ROOT_NAME = "sorting_tray"
_log_path: Path | None = None


def setup_logging(app_dir: Path) -> Path:
    global _log_path
    logs_dir = app_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    _log_path = logs_dir / "sorting_tray.log"

    root = logging.getLogger(ROOT_NAME)
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.propagate = False

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    file_handler = logging.FileHandler(_log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)-7s %(name)s: %(message)s"))
    root.addHandler(console)

    _install_excepthook(root)
    _install_qt_handler(root)

    root.info("=== session start (log: %s) ===", _log_path)
    return _log_path


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(ROOT_NAME).getChild(name)


def log_path() -> Path | None:
    return _log_path


def _install_excepthook(logger: logging.Logger) -> None:
    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logger.critical("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc, tb))

    sys.excepthook = hook


_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _install_qt_handler(logger: logging.Logger) -> None:
    qt_logger = logger.getChild("qt")

    def handler(mode, _context, message):
        qt_logger.log(_QT_LEVELS.get(mode, logging.INFO), "%s", message)

    qInstallMessageHandler(handler)
