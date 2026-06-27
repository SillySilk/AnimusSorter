"""Top control bar: open folder, category readout, sort, grid size, punch keys."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .models import Category
from .styles import PUNCH_KEY_QSS

log = get_logger("controlbar")

SORT_MODES = ["Filename", "Date modified", "File size", "Random"]


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


class ControlBar(QWidget):
    open_requested = pyqtSignal()
    sort_changed = pyqtSignal(str)
    grid_size_changed = pyqtSignal(int)
    armed_changed = pyqtSignal(int)  # latched bin index 0..7, or -1 for none

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(14)

        self.open_btn = QPushButton("Open Folder")
        self.open_btn.setMinimumHeight(40)
        self.open_btn.clicked.connect(self.open_requested)
        outer.addWidget(self.open_btn)

        self.category_label = QLabel("No project")
        self.category_label.setObjectName("categoryIndicator")
        outer.addWidget(self.category_label)

        outer.addWidget(QLabel("Sort"))
        self.sort_box = QComboBox()
        self.sort_box.addItems(SORT_MODES)
        self.sort_box.currentTextChanged.connect(self.sort_changed)
        outer.addWidget(self.sort_box)

        outer.addWidget(QLabel("Grid"))
        self.grid_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_slider.setMinimum(80)
        self.grid_slider.setMaximum(280)
        self.grid_slider.setValue(160)
        self.grid_slider.setFixedWidth(120)
        self.grid_slider.valueChanged.connect(self.grid_size_changed)
        outer.addWidget(self.grid_slider)

        outer.addStretch(1)

        outer.addWidget(self._build_punch_keys())

    def _build_punch_keys(self) -> QWidget:
        wrap = QWidget()
        grid = QHBoxLayout(wrap)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        self._armed = -1
        self.punch_keys: list[QPushButton] = []
        for i in range(8):
            key = QPushButton(str(i + 1))
            key.setObjectName("punchKey")
            key.setStyleSheet(PUNCH_KEY_QSS)
            key.setCheckable(True)
            key.setToolTip(f"Lock Bin {i + 1}: click images to send them there")
            key.clicked.connect(lambda _=False, idx=i: self._on_key(idx))
            grid.addWidget(key)
            self.punch_keys.append(key)
        return wrap

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
