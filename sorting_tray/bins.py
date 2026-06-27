"""The 8 bins (4x2 grid). Each bin is a sorting tray for one subject set.

A bin holds: a subject-count dropdown that spawns one name box per subject, and
a shrunken thumbnail strip of the images dropped into it. The name boxes are the
only free text the user types; everything else is derived.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .gallery import ID_ROLE, MIME_IDS, decode_ids
from .models import MAX_SUBJECTS_PER_BIN

log = get_logger("bins")

# Bin thumbnails are roughly a fifth of a gallery thumb — "shrunk like dropped
# in a magic bag", just enough to confirm the image landed.
STRIP_ICON = 40


class _DropStrip(QListWidget):
    """Thumbnail strip that accepts image-id drops and double-click-to-return."""

    images_dropped = pyqtSignal(list)
    return_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setMovement(QListWidget.Movement.Static)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setIconSize(QSize(STRIP_ICON, STRIP_ICON))
        self.setGridSize(QSize(STRIP_ICON + 6, STRIP_ICON + 6))
        self.setSpacing(2)
        # An item view delivers drag/drop to its VIEWPORT, which only accepts
        # drops when dragDropMode enables it. Without DropOnly the viewport's
        # acceptDrops stays false and our drop handlers never fire.
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setFrameShape(QListWidget.Shape.NoFrame)
        self.itemDoubleClicked.connect(self._on_double_click)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_IDS):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_IDS):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME_IDS):
            ids = decode_ids(event.mimeData().data(MIME_IDS))
            log.debug("drop on strip: ids=%s", ids)
            if ids:
                self.images_dropped.emit(ids)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _on_double_click(self, item):
        self.return_requested.emit([item.data(ID_ROLE)])

    def ids(self) -> list[int]:
        return [self.item(i).data(ID_ROLE) for i in range(self.count())]


class BinWidget(QGroupBox):
    """One bin. Authoritative for its own UI state (names + which images)."""

    images_dropped = pyqtSignal(int, list)   # bin_index, ids
    return_requested = pyqtSignal(int, list)  # bin_index, ids

    def __init__(self, index: int, parent=None):
        super().__init__(f"Bin {index + 1}", parent)
        self.index = index
        self._items: dict[int, QListWidgetItem] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 8)
        outer.setSpacing(4)

        # Big, bright, fancy label that names the bin once subjects are filled in
        # — like the label you slap on a sorting bin once you know what it holds.
        self.header = QLabel()
        self.header.setObjectName("binHeader")
        self.header.setWordWrap(True)
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header.setVisible(False)
        outer.addWidget(self.header)

        top = QHBoxLayout()
        top.addWidget(QLabel("Subjects"))
        self.count_box = QComboBox()
        self.count_box.addItems([str(n) for n in range(1, MAX_SUBJECTS_PER_BIN + 1)])
        self.count_box.currentIndexChanged.connect(self._rebuild_name_boxes)
        top.addWidget(self.count_box)
        top.addStretch(1)
        self.tally = QLabel("0")
        self.tally.setStyleSheet("color:#9aa;")
        top.addWidget(self.tally)
        outer.addLayout(top)

        self._names_box = QVBoxLayout()
        self._names_box.setSpacing(3)
        outer.addLayout(self._names_box)
        self._name_edits: list[QLineEdit] = []
        self._rebuild_name_boxes()

        self.strip = _DropStrip()
        self.strip.images_dropped.connect(lambda ids: self.images_dropped.emit(self.index, ids))
        self.strip.return_requested.connect(
            lambda ids: self.return_requested.emit(self.index, ids)
        )
        outer.addWidget(self.strip, 1)

    # --- name boxes -------------------------------------------------------
    def _rebuild_name_boxes(self) -> None:
        count = self.count_box.currentIndex() + 1
        existing = [e.text() for e in self._name_edits]
        while self._names_box.count():
            w = self._names_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._name_edits = []
        for i in range(count):
            edit = QLineEdit()
            edit.setPlaceholderText(f"Subject {i + 1} name")
            if i < len(existing):
                edit.setText(existing[i])
            edit.textChanged.connect(self._update_header)
            self._names_box.addWidget(edit)
            self._name_edits.append(edit)
        self._update_header()

    def _update_header(self) -> None:
        """Light up the bin's banner with its subject names, or hide it when blank."""
        names = [n.strip() for n in self.names() if n.strip()]
        if names:
            self.header.setText(" · ".join(names))
            self.header.setVisible(True)
        else:
            self.header.clear()
            self.header.setVisible(False)

    def names(self) -> list[str]:
        return [e.text() for e in self._name_edits]

    def subject_count(self) -> int:
        return len(self._name_edits)

    # --- thumbnails -------------------------------------------------------
    def add_image(self, image_id: int, pixmap: QPixmap | None, tooltip: str) -> None:
        if image_id in self._items:
            return
        item = QListWidgetItem()
        item.setData(ID_ROLE, image_id)
        item.setToolTip(tooltip)
        if pixmap is not None and not pixmap.isNull():
            item.setIcon(QIcon(pixmap))
        self.strip.addItem(item)
        self._items[image_id] = item
        self._update_tally()

    def set_thumb(self, image_id: int, pixmap: QPixmap) -> None:
        item = self._items.get(image_id)
        if item is not None:
            item.setIcon(QIcon(pixmap))

    def remove_ids(self, ids: list[int]) -> None:
        for image_id in ids:
            item = self._items.pop(image_id, None)
            if item is not None:
                self.strip.takeItem(self.strip.row(item))
        self._update_tally()

    def image_ids(self) -> list[int]:
        return self.strip.ids()

    def clear_images(self) -> None:
        self.strip.clear()
        self._items.clear()
        self._update_tally()

    def _update_tally(self) -> None:
        self.tally.setText(str(len(self._items)))

    # --- validation highlight --------------------------------------------
    def set_flagged(self, flagged: bool) -> None:
        self.setProperty("flagged", "true" if flagged else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_armed(self, armed: bool) -> None:
        """Highlight this bin as the current click target."""
        self.setProperty("armed", "true" if armed else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class BinPanel(QWidget):
    """The 4x2 grid holding all 8 bins."""

    images_dropped = pyqtSignal(int, list)
    return_requested = pyqtSignal(int, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("binPanel")
        grid = QGridLayout(self)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setSpacing(8)
        self.bins: list[BinWidget] = []
        for i in range(8):
            bw = BinWidget(i)
            bw.images_dropped.connect(self.images_dropped)
            bw.return_requested.connect(self.return_requested)
            grid.addWidget(bw, i // 2, i % 2)
            self.bins.append(bw)
        for c in range(2):
            grid.setColumnStretch(c, 1)
        for r in range(4):
            grid.setRowStretch(r, 1)
