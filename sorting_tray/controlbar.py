"""Top control bar: forge brand, open/category/sort/grid, Execute, radio presets.

Two-row left group (brand wordmark over the working controls + Execute) and a
recessed radio module on the right holding the eight mechanical preset keys.
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .assets import load_svg_pixmap
from .models import Category
from .painted import DebossedLabel

log = get_logger("controlbar")

SORT_MODES = ["Filename", "Date modified", "File size", "Random"]


class PunchKey(QPushButton):
    """A clunky face-on car-radio preset button, custom-painted: a big rectangular
    key that sinks into its bezel when latched (armed) and glows forge-ember. The
    button face carries its preset number and the bin's name.

    Latch/interlock semantics stay in QPushButton (checkable + clicked); only the
    look + the press travel animation are bespoke.
    """

    _W, _H = 100, 56
    _DEPTH = 16  # deep mechanical throw — the face plunges this far when pressed in

    def __init__(self, number: int, parent=None):
        super().__init__(str(number), parent)
        self._number = number
        self._name = ""
        self.setCheckable(True)
        self.setFixedSize(self._W, self._H)
        self._travel = 0.0
        self._anim = QPropertyAnimation(self, b"travel", self)
        self.toggled.connect(self._on_toggle)

    # animated 0 (out/rest) .. 1 (in/latched)
    def _get_travel(self) -> float:
        return self._travel

    def _set_travel(self, value: float) -> None:
        self._travel = value
        self.update()

    travel = pyqtProperty(float, _get_travel, _set_travel)

    def _on_toggle(self, checked: bool) -> None:
        self._anim.stop()
        if checked:
            # Slam in: fast plunge that decelerates hard into the stop — the clunk.
            self._anim.setDuration(85)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        else:
            # Spring out with a little mechanical pop.
            self._anim.setDuration(140)
            self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        self._name = name or ""
        detail = f": {self._name}" if self._name else ""
        self.setToolTip(f"Bin {self._number}{detail} — click images to send them here")
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            p.setOpacity(0.4)  # locked out while another key is armed

        checked = self.isChecked()
        w, h = self.width(), self.height()

        # 1) Chunky bezel frame.
        bezel = QRectF(0.5, 0.5, w - 1, h - 1)
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor("#3a352e"))
        bg.setColorAt(1, QColor("#15120f"))
        p.setPen(QPen(QColor("#0a0807"), 1))
        p.setBrush(bg)
        p.drawRoundedRect(bezel, 5, 5)

        # 2) Recessed dark well the button sits in.
        well = QRectF(3, 3, w - 6, h - 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#0c0a08"))
        p.drawRoundedRect(well, 4, 4)

        # 3) Button face — travels down into the well when pressed in.
        face_top = well.top() + 1 + self._travel * self._DEPTH
        face = QRectF(well.left() + 1, face_top, well.width() - 2, well.height() - 2 - self._DEPTH)
        fg = QLinearGradient(0, face.top(), 0, face.bottom())
        if checked:
            fg.setColorAt(0, QColor("#ff7a2a"))
            fg.setColorAt(1, QColor("#c23d0c"))
        else:
            fg.setColorAt(0, QColor("#5e564c"))
            fg.setColorAt(0.5, QColor("#3a352e"))
            fg.setColorAt(1, QColor("#2a251f"))
        p.setPen(QPen(QColor("#0a0807"), 1))
        p.setBrush(fg)
        p.drawRoundedRect(face, 4, 4)
        # Top highlight gives the raised cap its sheen (gone when sunk/ember).
        if not checked:
            p.setPen(QPen(QColor(255, 255, 255, 28), 1))
            p.drawLine(int(face.left()) + 4, int(face.top()) + 1, int(face.right()) - 4, int(face.top()) + 1)

        # 4) Face text: bin name once named (the number is dropped so it can't
        # collide with the name), or a big lone number while the bin is unnamed.
        if self._name:
            p.setPen(QColor("#1a0c04") if checked else QColor("#ece3d2"))
            p.setFont(QFont("Zilla Slab", 11, QFont.Weight.Bold))
            fm = QFontMetrics(p.font())
            elided = fm.elidedText(self._name, Qt.TextElideMode.ElideRight, int(face.width()) - 12)
            p.drawText(face.adjusted(4, 2, -4, -2), int(Qt.AlignmentFlag.AlignCenter), elided)
        else:
            p.setPen(QColor("#1a0c04") if checked else QColor("#e6dccb"))
            p.setFont(QFont("Zilla Slab", 17, QFont.Weight.Bold))
            p.drawText(face, int(Qt.AlignmentFlag.AlignCenter), str(self._number))
        p.end()


class CategoryDialog(QDialog):
    """Asked once at project open. The choice locks the third filename field."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Category")
        self.choice: Category | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("What does this project sort?\nThis locks the category for every file."))
        row = QHBoxLayout()
        for cat in Category:
            btn = QPushButton(cat.value)
            btn.setMinimumHeight(48)
            btn.clicked.connect(lambda _=False, c=cat: self._pick(c))
            row.addWidget(btn)
        layout.addLayout(row)

    def _pick(self, cat: Category) -> None:
        self.choice = cat
        self.accept()


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionLabel")
    return lbl


class ControlBar(QWidget):
    open_requested = pyqtSignal()
    sort_changed = pyqtSignal(str)
    grid_size_changed = pyqtSignal(int)
    armed_changed = pyqtSignal(int)  # latched bin index 0..7, or -1 for none
    sound_toggled = pyqtSignal(bool)  # True == muted
    settings_requested = pyqtSignal()  # open the LM Studio settings dialog

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("controlBar")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(13, 13, 13, 13)
        outer.setSpacing(14)

        outer.addLayout(self._build_left_group(), 1)
        outer.addWidget(self._build_radio_module(), 0)

    # --- left group -------------------------------------------------------
    def _build_left_group(self) -> QVBoxLayout:
        left = QVBoxLayout()
        left.setSpacing(10)

        # Row A: forge badge + debossed wordmark stack.
        row_a = QHBoxLayout()
        row_a.setSpacing(10)
        badge = QLabel()
        badge.setObjectName("forgeBadge")
        badge.setFixedSize(42, 42)
        badge.setPixmap(load_svg_pixmap("anvil", "#2a1d08", 26))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row_a.addWidget(badge)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        self.wordmark = DebossedLabel("ANIMUS SORTER", QFont("Ultra", 19), "#cf965d")
        brand_col.addWidget(self.wordmark)
        subtitle = QLabel("THING-O-MATIC CORPORATION")
        subtitle.setObjectName("brandSubtitle")
        brand_col.addWidget(subtitle)
        row_a.addLayout(brand_col)
        row_a.addStretch(1)
        left.addLayout(row_a)

        # Row B: open / category / sort / grid / execute.
        row_b = QHBoxLayout()
        row_b.setSpacing(12)

        self.open_btn = QPushButton("OPEN FOLDER")
        self.open_btn.setObjectName("openButton")
        self.open_btn.setMinimumHeight(42)
        self.open_btn.clicked.connect(self.open_requested)
        row_b.addWidget(self.open_btn)

        cat_col = QVBoxLayout()
        cat_col.setSpacing(2)
        cat_col.addWidget(_section_label("PROJECT"))
        self.category_label = QLabel("NO PROJECT")
        self.category_label.setObjectName("categoryIndicator")
        cat_col.addWidget(self.category_label)
        row_b.addLayout(cat_col)

        sort_col = QVBoxLayout()
        sort_col.setSpacing(2)
        sort_col.addWidget(_section_label("SORT"))
        self.sort_box = QComboBox()
        self.sort_box.addItems(SORT_MODES)
        self.sort_box.currentTextChanged.connect(self.sort_changed)
        sort_col.addWidget(self.sort_box)
        row_b.addLayout(sort_col)

        grid_col = QVBoxLayout()
        grid_col.setSpacing(2)
        grid_col.addWidget(_section_label("THUMB"))
        self.grid_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_slider.setMinimum(80)
        self.grid_slider.setMaximum(280)
        self.grid_slider.setValue(160)
        self.grid_slider.setFixedWidth(120)
        self.grid_slider.valueChanged.connect(self.grid_size_changed)
        grid_col.addWidget(self.grid_slider)
        row_b.addLayout(grid_col)

        # Execute is mounted here later by MainWindow (mount_execute).
        self._execute_slot = QHBoxLayout()
        self._execute_slot.setContentsMargins(0, 0, 0, 0)
        row_b.addLayout(self._execute_slot)

        self.settings_btn = QPushButton("AI")
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setToolTip("LM Studio settings (Analyze / Auto-sort)")
        self.settings_btn.setFixedWidth(38)
        self.settings_btn.setMinimumHeight(42)
        self.settings_btn.clicked.connect(self.settings_requested)
        row_b.addWidget(self.settings_btn)

        row_b.addStretch(1)
        left.addLayout(row_b)
        return left

    def mount_execute(self, button: QPushButton) -> None:
        """Host the MainWindow-owned Execute button in the control bar."""
        button.setParent(self)
        self._execute_slot.addWidget(button)

    # --- radio module -----------------------------------------------------
    def _build_radio_module(self) -> QWidget:
        bezel = QWidget()
        bezel.setObjectName("radioBezel")
        col = QVBoxLayout(bezel)
        col.setContentsMargins(10, 8, 10, 10)
        col.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        flame = QLabel()
        flame.setPixmap(load_svg_pixmap("flame", "#b88a3c", 12))
        header.addWidget(flame)
        title = QLabel("MOVE TO BIN")
        title.setObjectName("radioTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.snd_toggle = QPushButton("SND ON")
        self.snd_toggle.setObjectName("sndToggle")
        self.snd_toggle.setCheckable(True)
        self.snd_toggle.clicked.connect(self._on_sound_toggle)
        header.addWidget(self.snd_toggle)

        presets_lbl = QLabel("PRESETS 1—8")
        presets_lbl.setObjectName("sectionLabel")
        header.addWidget(presets_lbl)
        col.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #b88a3c; background: #5e451f; max-height: 1px;")
        col.addWidget(divider)

        col.addLayout(self._build_punch_keys())
        return bezel

    def _on_sound_toggle(self, checked: bool) -> None:
        self.snd_toggle.setText("SND OFF" if checked else "SND ON")
        self.sound_toggled.emit(checked)

    def _build_punch_keys(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        self._armed = -1
        self.punch_keys: list[PunchKey] = []
        for i in range(8):
            key = PunchKey(i + 1)
            key.setObjectName("punchKey")
            key.set_name("")  # also sets the tooltip
            key.clicked.connect(lambda _=False, idx=i: self._on_key(idx))
            row, col = divmod(i, 4)  # 2 rows x 4 columns
            grid.addWidget(key, row, col)
            self.punch_keys.append(key)
        return grid

    def set_key_label(self, index: int, name: str) -> None:
        """Print a bin's current name on its preset key (full name on hover)."""
        if 0 <= index < len(self.punch_keys):
            self.punch_keys[index].set_name(name or "")

    def _on_key(self, idx: int) -> None:
        """Latching radio: press to arm a bin, press again to release. While one
        is armed the other seven gray out, so the only live key is the lit one."""
        if self._armed == idx:
            self._armed = -1
        else:
            self._armed = idx
        log.debug("punch key %s -> armed=%s", idx + 1, self._armed)
        for j, key in enumerate(self.punch_keys):
            armed = self._armed == j
            key.setChecked(armed)
            # When something is armed, only the armed key stays live.
            key.setEnabled(self._armed < 0 or armed)
        self.armed_changed.emit(self._armed)

    def disarm(self) -> None:
        self._armed = -1
        for key in self.punch_keys:
            key.setChecked(False)
            key.setEnabled(True)
        self.armed_changed.emit(-1)

    def set_category(self, category: Category) -> None:
        self.category_label.setText(category.value.upper())
