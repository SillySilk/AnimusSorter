"""The 8 bins (4x2 grid). Each bin is a metal parts-tray for one subject set.

A bin has three stacked areas: a title row (number tab + auto-name + tally), an
enlarged drop window (the thumbnail strip), and an input area (a -/+ subject
stepper plus a copper name plate holding the editable name boxes). The name
boxes are the only free text the user types; everything else is derived.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QFont,
    QFontMetrics,
    QIcon,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .gallery import ID_ROLE, MIME_IDS, decode_ids
from .models import MAX_SUBJECTS_PER_BIN
from .painted import draw_tray_shell

log = get_logger("bins")

# Bin thumbnails are small — just enough to confirm the image landed.
STRIP_ICON = 28

# Analyze needs a few examples to characterize a subject; 5 is the floor, no ceiling.
ANALYZE_MIN_IMAGES = 5
# Categories where subject detection makes sense (Style is about art, not subjects).
ANALYZE_CATEGORIES = {"Character", "Object"}


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class FitLabel(QLabel):
    """A single-line label that auto-shrinks its font so the full text always
    fits the label's width (down to a floor) instead of being clipped. The bin
    name banner uses this so a long name like 'Homer · Marge · Lisa' stays
    readable rather than running off the plate.

    Size is applied via a per-widget inline stylesheet (px) rather than setFont:
    the app's global `QWidget { font-size: 13px }` rule would otherwise override
    setFont and defeat the shrink. The base #binHeader rule still supplies color.
    """

    def __init__(self, text: str = "", base_px: int = 15, min_px: int = 8, parent=None):
        super().__init__(text, parent)
        self._base_px = base_px
        self._min_px = min_px
        self._cur_px = -1
        self._apply_px(base_px)

    def setText(self, text: str) -> None:  # noqa: N802 (Qt override)
        super().setText(text)
        self._refit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refit()

    def _apply_px(self, px: int) -> None:
        if px == self._cur_px:
            return
        self._cur_px = px
        # Inline (per-widget) stylesheet beats the global QWidget font-size.
        self.setStyleSheet(f'font-family: "Zilla Slab"; font-weight: 700; font-size: {px}px;')

    def _refit(self) -> None:
        avail = self.width() - 10  # leave room for the 4px QSS side padding
        if avail <= 0:
            return
        text = self.text()
        px = self._base_px
        while px > self._min_px:
            f = QFont("Zilla Slab", -1, QFont.Weight.Bold)
            f.setPixelSize(px)
            if QFontMetrics(f).horizontalAdvance(text) <= avail:
                break
            px -= 1
        self._apply_px(px)


class _DropStrip(QListWidget):
    """Thumbnail strip that accepts image-id drops and double-click-to-return."""

    images_dropped = pyqtSignal(list)
    return_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropStrip")
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
    names_changed = pyqtSignal(int, str)      # bin_index, display name ("" if blank)
    analyze_requested = pyqtSignal(int)       # bin_index — run vision analysis
    autosort_requested = pyqtSignal(int)      # bin_index — scan tray for matches

    def __init__(self, index: int, parent=None):
        super().__init__("", parent)
        self.setObjectName("binWidget")
        self.index = index
        self._items: dict[int, QListWidgetItem] = {}
        self._count = 1
        self._category = "Character"
        # Session-only recognition profile built by Analyze; drives Auto-sort.
        self.roster: dict[str, str] = {}
        self.analyzed = False

        outer = QVBoxLayout(self)
        # Margins clear the metal walls painted in paintEvent; generous so the
        # stacked rows don't feel jammed against the shell.
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(8)

        outer.addLayout(self._build_title_row())

        # 2) Drop window — the enlarged drop target.
        self.strip = _DropStrip()
        self.strip.setMinimumHeight(50)
        self.strip.images_dropped.connect(lambda ids: self.images_dropped.emit(self.index, ids))
        self.strip.return_requested.connect(
            lambda ids: self.return_requested.emit(self.index, ids)
        )
        outer.addWidget(self.strip, 1)

        outer.addLayout(self._build_input_area())
        self._rebuild_name_boxes()

    # --- custom metal shell ----------------------------------------------
    def paintEvent(self, _event):
        """Draw a square, shallow riveted parts tray — a flat rectangular bin
        you sort into, NOT a radio/wedge. Shares draw_tray_shell with the big
        gallery tray so both read as the same family of object."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        draw_tray_shell(
            p,
            self.width(),
            self.height(),
            armed=self.property("armed") == "true",
            flagged=self.property("flagged") == "true",
        )
        p.end()

    # --- area builders ----------------------------------------------------
    def _build_title_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        self._number_tab = QLabel(str(self.index + 1))
        self._number_tab.setObjectName("binNumberTab")
        self._number_tab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._number_tab)

        # Auto-name banner — lights up with the bin's subject names and
        # auto-shrinks the font so a long name never runs off the plate.
        self.header = FitLabel("UNNAMED", base_px=15)
        self.header.setObjectName("binHeader")
        self.header.setWordWrap(False)
        row.addWidget(self.header, 1)

        self.tally = QLabel("00")
        self.tally.setObjectName("binTally")
        self.tally.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.tally)
        return row

    def _build_input_area(self) -> QVBoxLayout:
        area = QVBoxLayout()
        area.setSpacing(4)

        stepper = QHBoxLayout()
        stepper.setSpacing(4)
        subj = QLabel("SUBJ")
        subj.setObjectName("subjLabel")
        stepper.addWidget(subj)
        self._minus_btn = QPushButton("−")  # minus sign
        self._minus_btn.setObjectName("stepperButton")
        self._minus_btn.clicked.connect(self._dec)
        stepper.addWidget(self._minus_btn)
        self._count_label = QLabel("1")
        self._count_label.setObjectName("stepperCount")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stepper.addWidget(self._count_label)
        self._plus_btn = QPushButton("+")
        self._plus_btn.setObjectName("stepperButton")
        self._plus_btn.clicked.connect(self._inc)
        stepper.addWidget(self._plus_btn)
        stepper.addStretch(1)
        self.filename_preview = QLabel("")
        self.filename_preview.setObjectName("filenamePreview")
        stepper.addWidget(self.filename_preview)
        area.addLayout(stepper)

        # Copper name plate hosting the editable name boxes.
        self._plate = QWidget()
        self._plate.setObjectName("copperPlate")
        self._names_box = QVBoxLayout(self._plate)
        self._names_box.setContentsMargins(6, 4, 6, 4)
        self._names_box.setSpacing(3)
        self._name_edits: list[QLineEdit] = []
        area.addWidget(self._plate)

        # AI assist row: Analyze (build a recognition profile) + Auto-sort (file matches).
        ai_row = QHBoxLayout()
        ai_row.setSpacing(6)
        self._analyze_btn = QPushButton("ANALYZE")
        self._analyze_btn.setObjectName("analyzeButton")
        self._analyze_btn.clicked.connect(lambda: self.analyze_requested.emit(self.index))
        ai_row.addWidget(self._analyze_btn)
        self._autosort_btn = QPushButton("AUTO-SORT TRAY")
        self._autosort_btn.setObjectName("autosortButton")
        self._autosort_btn.clicked.connect(lambda: self.autosort_requested.emit(self.index))
        ai_row.addWidget(self._autosort_btn)
        area.addLayout(ai_row)
        return area

    # --- subject stepper --------------------------------------------------
    def _inc(self) -> None:
        self._set_subject_count(self._count + 1)

    def _dec(self) -> None:
        self._set_subject_count(self._count - 1)

    def _set_subject_count(self, n: int) -> None:
        n = max(1, min(MAX_SUBJECTS_PER_BIN, n))
        if n == self._count and self._name_edits:
            return
        self._count = n
        self._count_label.setText(str(n))
        self._rebuild_name_boxes()

    # --- name boxes -------------------------------------------------------
    def _rebuild_name_boxes(self) -> None:
        existing = [e.text() for e in self._name_edits]
        while self._names_box.count():
            w = self._names_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._name_edits = []
        for i in range(self._count):
            edit = QLineEdit()
            edit.setPlaceholderText(f"Subject {i + 1} name")
            if i < len(existing):
                edit.setText(existing[i])
            edit.textChanged.connect(self._on_names_changed)
            self._names_box.addWidget(edit)
            self._name_edits.append(edit)
        self._on_names_changed()

    def _on_names_changed(self) -> None:
        self._update_header()
        self._update_preview()
        # Editing names invalidates a stale recognition profile.
        if self.analyzed:
            self.analyzed = False
            self.roster = {}
        self._refresh_ai_buttons()
        names = [n.strip() for n in self.names() if n.strip()]
        self.names_changed.emit(self.index, " · ".join(names))

    def _update_header(self) -> None:
        """Light up the banner with subject names, or show UNNAMED when blank."""
        names = [n.strip() for n in self.names() if n.strip()]
        self.header.setText(" · ".join(names) if names else "UNNAMED")

    def _update_preview(self) -> None:
        names = [n.strip() for n in self.names() if n.strip()]
        block = "-".join(names) if names else "?"
        self.filename_preview.setText(f"{block}_001_{self._category}")

    def set_category_label(self, category: str) -> None:
        self._category = category
        self._update_preview()
        self._refresh_ai_buttons()

    def names(self) -> list[str]:
        return [e.text() for e in self._name_edits]

    def subject_count(self) -> int:
        return len(self._name_edits)

    # --- AI assist gating -------------------------------------------------
    def analyze_enabled(self) -> bool:
        """Analyze is live only on a detectable category, with enough images, all named."""
        names = [n.strip() for n in self.names()]
        return (
            self._category in ANALYZE_CATEGORIES
            and len(self._items) >= ANALYZE_MIN_IMAGES
            and bool(names) and all(names)
        )

    def autosort_enabled(self) -> bool:
        """Auto-sort needs a confirmed roster covering every named subject."""
        names = {n.strip() for n in self.names() if n.strip()}
        return bool(self.analyzed and names and names <= set(self.roster))

    def set_roster(self, roster: dict) -> None:
        self.roster = dict(roster)
        self.analyzed = bool(roster)
        self._refresh_ai_buttons()

    def set_busy(self, busy: bool) -> None:
        """Disable both AI buttons while a run is in flight."""
        self._busy = busy
        self._refresh_ai_buttons()

    def _refresh_ai_buttons(self) -> None:
        busy = getattr(self, "_busy", False)
        self._analyze_btn.setEnabled(self.analyze_enabled() and not busy)
        self._autosort_btn.setEnabled(self.autosort_enabled() and not busy)

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
        n = len(self._items)
        self.tally.setText(f"{n:02d}")
        self.tally.setProperty("hot", "true" if n > 0 else "false")
        _repolish(self.tally)
        self._refresh_ai_buttons()  # crossing the 5-image floor flips Analyze

    # --- validation / armed highlight ------------------------------------
    def set_flagged(self, flagged: bool) -> None:
        self.setProperty("flagged", "true" if flagged else "false")
        _repolish(self)
        self.update()  # repaint the trapezoid ring

    def set_armed(self, armed: bool) -> None:
        """Highlight this bin as the current click target."""
        val = "true" if armed else "false"
        for w in (self, self.header, self._number_tab, self.strip):
            w.setProperty("armed", val)
            _repolish(w)
        self.update()  # repaint the trapezoid shell/ring


class BinPanel(QWidget):
    """The 4x2 grid holding all 8 bins."""

    images_dropped = pyqtSignal(int, list)
    return_requested = pyqtSignal(int, list)
    names_changed = pyqtSignal(int, str)
    analyze_requested = pyqtSignal(int)
    autosort_requested = pyqtSignal(int)

    _MARGIN = 10
    _HSPACE = 14
    _VSPACE = 14
    _COLS = 2
    _ROWS = 4
    _MIN_SIDE = 150  # don't crush the stacked content below this
    _MAX_SIDE = 480  # don't balloon on an ultrawide monitor

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("binPanel")
        grid = QGridLayout(self)
        grid.setContentsMargins(self._MARGIN, self._MARGIN, self._MARGIN, self._MARGIN)
        grid.setHorizontalSpacing(self._HSPACE)
        grid.setVerticalSpacing(self._VSPACE)
        self.bins: list[BinWidget] = []
        for i in range(8):
            bw = BinWidget(i)
            bw.images_dropped.connect(self.images_dropped)
            bw.return_requested.connect(self.return_requested)
            bw.names_changed.connect(self.names_changed)
            bw.analyze_requested.connect(self.analyze_requested)
            bw.autosort_requested.connect(self.autosort_requested)
            # Center each square within its (possibly larger) grid cell.
            grid.addWidget(bw, i // 2, i % 2, Qt.AlignmentFlag.AlignCenter)
            self.bins.append(bw)
        for c in range(self._COLS):
            grid.setColumnStretch(c, 1)
        for r in range(self._ROWS):
            grid.setRowStretch(r, 1)

    def resizeEvent(self, event):
        """Size each tray to a true square that fills its column, then publish the
        full stacked height as our minimum so the host QScrollArea grows a
        vertical scrollbar instead of shrinking the squares to fit. Big trays,
        scroll to reach the lower ones."""
        super().resizeEvent(event)
        avail_w = self.width() - 2 * self._MARGIN - (self._COLS - 1) * self._HSPACE
        side = max(self._MIN_SIDE, min(self._MAX_SIDE, int(avail_w / self._COLS)))
        for bw in self.bins:
            bw.setFixedSize(side, side)
        # Total height of all four rows — drives the scrollbar when it exceeds
        # the viewport. Set as minimumHeight so the scroll area honors it.
        total_h = self._ROWS * side + (self._ROWS - 1) * self._VSPACE + 2 * self._MARGIN
        self.setMinimumHeight(total_h)
