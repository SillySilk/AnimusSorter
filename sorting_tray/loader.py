"""Background thumbnail loading.

Decoding hundreds of scraped images on the GUI thread would freeze the window,
so thumbnails are generated in a thread pool with Pillow and handed back to the
GUI as QImages (QPixmap must be built on the GUI thread, so the slot converts).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

# Generated once at this size; the grid slider scales the displayed icon up or
# down from here without re-decoding the file.
THUMB_BASE = 320


class _LoaderSignals(QObject):
    thumb_ready = pyqtSignal(int, object)  # image id, QImage
    finished = pyqtSignal()


class _ThumbTask(QRunnable):
    def __init__(self, image_id: int, path: Path, signals: _LoaderSignals):
        super().__init__()
        self.image_id = image_id
        self.path = path
        self.signals = signals

    def run(self) -> None:
        from PyQt6.QtGui import QImage

        try:
            with Image.open(self.path) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((THUMB_BASE, THUMB_BASE))
                img = img.convert("RGBA")
                data = img.tobytes("raw", "RGBA")
                qimg = QImage(
                    data, img.width, img.height, QImage.Format.Format_RGBA8888
                ).copy()  # copy detaches from the soon-freed `data` buffer
            self.signals.thumb_ready.emit(self.image_id, qimg)
        except Exception:
            # Unreadable file: emit a null image so the cell shows a placeholder.
            from PyQt6.QtGui import QImage as _QImage

            self.signals.thumb_ready.emit(self.image_id, _QImage())


class ThumbnailLoader(QObject):
    """Owns a thread pool and emits one `thumb_ready` per queued image."""

    thumb_ready = pyqtSignal(int, object)
    finished = pyqtSignal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._signals = _LoaderSignals()
        self._signals.thumb_ready.connect(self.thumb_ready)
        self._pending = 0
        self._done = 0

    def load(self, items: list[tuple[int, Path]]) -> None:
        self._pending = len(items)
        self._done = 0
        if not items:
            self.finished.emit()
            return
        self._signals.thumb_ready.connect(self._tick)
        for image_id, path in items:
            self._pool.start(_ThumbTask(image_id, path, self._signals))

    def _tick(self, *_args) -> None:
        self._done += 1
        if self._done >= self._pending:
            self._signals.thumb_ready.disconnect(self._tick)
            self.finished.emit()
