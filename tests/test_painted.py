"""Headless guards for the two-pass engraved/stamped text labels."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from sorting_tray.painted import DebossedLabel, StampedLabel

_app = QApplication.instance() or QApplication([])


def test_debossed_label_constructs():
    lbl = DebossedLabel("ANIMUS SORTER", QFont("Zilla Slab", 19), "#cf965d")
    assert lbl.text() == "ANIMUS SORTER"
    assert lbl.sizeHint().width() > 0 and lbl.sizeHint().height() > 0
    assert not lbl.grab().isNull()


def test_stamped_label_constructs_and_rotates():
    lbl = StampedLabel("THING-O-MATIC CORP.", QFont("Alfa Slab One", 19), "#15110b", rotate_deg=-0.8)
    assert lbl.sizeHint().height() > 0
    lbl.setText("CHANGED")
    assert lbl.text() == "CHANGED"
    assert not lbl.grab().isNull()
