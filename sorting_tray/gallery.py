"""The gallery / sorting tray: a resizable thumbnail grid, one tile at a time.

Built on QListWidget in IconMode. SingleSelection with the rubber-band rect
disabled means a press-and-drag picks up the single tile under the cursor and
never draws a multi-select box. Each item carries its image id in the UserRole;
drags export that id via a private mime type the bins read.
"""

from __future__ import annotations

from PyQt6.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QFont,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .assets import load_svg_pixmap
from .painted import StampedLabel, draw_tray_shell

log = get_logger("gallery")

MIME_IDS = "application/x-sorting-tray-ids"

ID_ROLE = Qt.ItemDataRole.UserRole

# How far the mouse wheel scrolls per notch, in grid rows. The default per-item
# scrolling jumps most of a page over tall thumbnail cells; one row feels right.
WHEEL_ROWS_PER_NOTCH = 1.0


def encode_ids(ids: list[int]) -> bytes:
    return ",".join(str(i) for i in ids).encode("ascii")


def decode_ids(raw: bytes) -> list[int]:
    text = bytes(raw).decode("ascii").strip()
    return [int(p) for p in text.split(",") if p]


class Gallery(QListWidget):
    selection_changed = pyqtSignal()
    trash_requested = pyqtSignal(list)  # ids to delete from disk
    tile_activated = pyqtSignal(int)    # armed-mode click: send this id to the bin

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[int, QListWidgetItem] = {}
        self._armed_mode = False
        self._icon = 160
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        # One tile at a time, like handling physical prints. SingleSelection plus
        # a hidden selection rect means a press-and-drag picks up the tile under
        # the cursor and never draws a rubber-band multi-select box.
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setSelectionRectVisible(False)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        # Pixel-smooth scrolling so the wheel can move by a controlled amount
        # rather than snapping a whole (tall) item per step.
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setUniformItemSizes(True)
        self.setWordWrap(True)
        self.setSpacing(8)
        self._apply_icon_size()
        self.itemSelectionChanged.connect(self.selection_changed)

    # --- population -------------------------------------------------------
    def repopulate(self, ordered: list[tuple[int, str]]) -> None:
        """Replace all items in the given order. `ordered` is (id, label)."""
        prev_icons = {iid: it.icon() for iid, it in self._items.items()}
        self.clear()
        self._items.clear()
        cell = self._cell_size()
        for image_id, label in ordered:
            item = QListWidgetItem(label)
            item.setData(ID_ROLE, image_id)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            # Explicit size hint: thumbnails load async, so without this the item
            # stays text-label sized (~84x13) and only that strip is clickable —
            # clicking the thumbnail itself misses the item entirely.
            item.setSizeHint(cell)
            if image_id in prev_icons:
                item.setIcon(prev_icons[image_id])
            self.addItem(item)
            self._items[image_id] = item

    def set_thumb(self, image_id: int, pixmap: QPixmap) -> None:
        item = self._items.get(image_id)
        if item is not None:
            item.setIcon(QIcon(pixmap))

    def remove_ids(self, ids: list[int]) -> None:
        for image_id in ids:
            item = self._items.pop(image_id, None)
            if item is not None:
                self.takeItem(self.row(item))

    # --- selection --------------------------------------------------------
    def selected_ids(self) -> list[int]:
        return [it.data(ID_ROLE) for it in self.selectedItems()]

    def set_armed_mode(self, on: bool) -> None:
        """Armed: a single click shoots one image to the locked bin, so disable
        selection and drag. Disarmed: restore single-tile selection + drag."""
        self._armed_mode = on
        if on:
            self.clearSelection()
            self.setSelectionMode(QListWidget.SelectionMode.NoSelection)
            self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        else:
            self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            self.setDragDropMode(QListWidget.DragDropMode.DragOnly)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Scroll about one grid row per wheel notch instead of nearly a page."""
        dy = event.angleDelta().y()
        if dy == 0:
            super().wheelEvent(event)
            return
        notches = dy / 120.0  # one standard wheel notch = 120 units
        step = notches * WHEEL_ROWS_PER_NOTCH * self._cell_size().height()
        bar = self.verticalScrollBar()
        bar.setValue(bar.value() - int(round(step)))
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """In armed mode a left-press on a tile fires it straight to the bin,
        bypassing selection/itemClicked quirks. Otherwise normal press (which
        begins a drag in disarmed mode)."""
        if self._armed_mode and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            if item is not None:
                self.tile_activated.emit(item.data(ID_ROLE))
                event.accept()
                return
        super().mousePressEvent(event)

    # --- grid size --------------------------------------------------------
    def set_icon_size(self, px: int) -> None:
        self._icon = px
        self._apply_icon_size()

    def _cell_size(self) -> QSize:
        # Icon plus room for the filename label beneath it. Used as both the grid
        # cell and each item's size hint so the whole tile is clickable.
        return QSize(self._icon + 16, self._icon + 36)

    def _apply_icon_size(self) -> None:
        self.setIconSize(QSize(self._icon, self._icon))
        self.setGridSize(QSize(self._icon + 24, self._icon + 40))
        cell = self._cell_size()
        for item in self._items.values():
            item.setSizeHint(cell)

    # --- trash junk -------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            ids = self.selected_ids()
            if ids:
                self.trash_requested.emit(ids)
            return
        super().keyPressEvent(event)

    # --- drag out ---------------------------------------------------------
    def startDrag(self, supported_actions):  # type: ignore[override]
        log.debug("startDrag: selected ids=%s", self.selected_ids())
        super().startDrag(supported_actions)

    def mimeData(self, items):  # type: ignore[override]
        ids = [it.data(ID_ROLE) for it in items]
        log.debug("mimeData built for drag: ids=%s", ids)
        data = QMimeData()
        data.setData(MIME_IDS, encode_ids(ids))
        return data


def _repolish(widget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class GalleryFrame(QWidget):
    """The big sorting tray: one large riveted sheet-metal tray (same family as
    the bins, just oversized) holding the stamped factory header, a status line
    and the thumbnail cavity below — an object sitting on the floor, not the
    whole left field."""

    def __init__(self, gallery: Gallery, parent=None):
        super().__init__(parent)
        self.setObjectName("galleryFrame")
        self.gallery = gallery
        self.gallery.setObjectName("galleryList")

        col = QVBoxLayout(self)
        # Clear the painted tray walls + rivets so content sits inside the tray.
        col.setContentsMargins(16, 14, 16, 16)
        col.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)
        anvil = QLabel()
        anvil.setPixmap(load_svg_pixmap("anvil", "#15110b", 26))
        header.addWidget(anvil)

        stamp_col = QVBoxLayout()
        stamp_col.setSpacing(0)
        self._stamp = StampedLabel(
            "THING-O-MATIC CORP.", QFont("Alfa Slab One", 19), "#15110b", rotate_deg=-0.8
        )
        stamp_col.addWidget(self._stamp)
        sub = QLabel("DO NOT MOVE FROM SORTING FLOOR")
        sub.setStyleSheet(
            "color:#1d150d; font-family:'Zilla Slab'; font-weight:700;"
            "font-size:11px; letter-spacing:2px;"
        )
        stamp_col.addWidget(sub)
        header.addLayout(stamp_col)
        header.addStretch(1)

        self.status = QLabel("0 PRINTS UNSORTED")
        self.status.setObjectName("galleryStatus")
        header.addWidget(self.status, 0, Qt.AlignmentFlag.AlignTop)
        col.addLayout(header)

        col.addWidget(self.gallery, 1)

    def paintEvent(self, _event):
        """Paint the oversized riveted tray shell behind the header + cavity."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_tray_shell(
            p, self.width(), self.height(),
            armed=self.property("armed") == "true",
        )
        p.end()

    def set_status(self, text: str, armed: bool = False) -> None:
        self.status.setText(text)
        val = "true" if armed else "false"
        for w in (self.status, self.gallery, self):
            w.setProperty("armed", val)
            _repolish(w)
        self.update()  # repaint the tray shell ring
