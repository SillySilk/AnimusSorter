"""Background workers for Analyze + Auto-sort.

Thin Qt threads over the pure `llm` domain calls so the window never blocks. They
carry no business rules beyond orchestration — the matching decision lives in
`llm.is_exact_match`.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from .applog import get_logger
from . import llm

log = get_logger("analysis")


class AnalyzeWorker(QThread):
    """Identify the distinct recurring subjects in one bin's images."""

    finished_ok = pyqtSignal(list)  # list[Figure]
    failed = pyqtSignal(str)

    def __init__(self, image_paths, subject_names, category, url, model, parent=None):
        super().__init__(parent)
        self._image_paths = list(image_paths)
        self._subject_names = list(subject_names)
        self._category = category
        self._url = url
        self._model = model

    def run(self):
        try:
            figures = llm.analyze_bin(
                self._image_paths, self._subject_names, self._category, self._url, self._model
            )
            if not figures:
                self.failed.emit(
                    "The model couldn't distinguish any subjects — try clearer or more "
                    "varied images."
                )
                return
            self.finished_ok.emit(figures)
        except Exception as exc:  # noqa: BLE001 — surface to the UI
            log.exception("analyze failed")
            self.failed.emit(str(exc))


class AutoSortWorker(QThread):
    """Scan tray images and flag the ones that exactly match the bin's roster."""

    progress = pyqtSignal(int, int, int)  # scanned, total, filed
    matched = pyqtSignal(int)             # image_id to file into the bin
    finished_ok = pyqtSignal(int, int)    # filed, scanned
    failed = pyqtSignal(str)

    def __init__(self, items, roster, bin_names, category, url, model, parent=None):
        super().__init__(parent)
        self._items = list(items)  # list[(image_id, image_path)]
        self._roster = dict(roster)
        self._bin_names = list(bin_names)
        self._category = category
        self._url = url
        self._model = model
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = len(self._items)
        filed = 0
        scanned = 0
        try:
            for image_id, path in self._items:
                if self._cancelled:
                    break
                scanned += 1
                try:
                    res = llm.match_image(
                        path, self._roster, self._category, self._url, self._model
                    )
                    if llm.is_exact_match(res["present"], res["outsiders"], self._bin_names):
                        filed += 1
                        self.matched.emit(image_id)
                except Exception as exc:  # noqa: BLE001 — skip one bad image, keep scanning
                    log.warning("match skipped for id=%s: %s", image_id, exc)
                self.progress.emit(scanned, total, filed)
            self.finished_ok.emit(filed, scanned)
        except Exception as exc:  # noqa: BLE001
            log.exception("auto-sort failed")
            self.failed.emit(str(exc))
