"""Headless guards for the restructured bin widget + subject stepper."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from sorting_tray.bins import BinWidget
from sorting_tray.models import MAX_SUBJECTS_PER_BIN

_app = QApplication.instance() or QApplication([])


def test_starts_with_one_name_box():
    bw = BinWidget(0)
    assert bw.subject_count() == 1
    assert len(bw.names()) == 1


def test_plus_adds_box_and_preserves_text():
    bw = BinWidget(0)
    bw._name_edits[0].setText("Aria")
    bw._inc()
    assert bw.subject_count() == 2
    assert bw.names()[0] == "Aria"


def test_minus_removes_box():
    bw = BinWidget(0)
    bw._inc()
    assert bw.subject_count() == 2
    bw._dec()
    assert bw.subject_count() == 1


def test_clamps_at_bounds():
    bw = BinWidget(0)
    for _ in range(MAX_SUBJECTS_PER_BIN + 3):
        bw._inc()
    assert bw.subject_count() == MAX_SUBJECTS_PER_BIN
    for _ in range(MAX_SUBJECTS_PER_BIN + 3):
        bw._dec()
    assert bw.subject_count() == 1


def test_filename_preview_updates():
    bw = BinWidget(0)
    bw.set_category_label("Character")
    bw._name_edits[0].setText("Aria")
    assert "Aria_001_Character" in bw.filename_preview.text()


def test_names_changed_signal_emits_display_name():
    bw = BinWidget(3)
    seen = []
    bw.names_changed.connect(lambda idx, name: seen.append((idx, name)))
    bw._name_edits[0].setText("Aria")
    assert seen[-1] == (3, "Aria")
    bw._inc()
    bw._name_edits[1].setText("Garden")
    assert seen[-1] == (3, "Aria · Garden")
    bw._name_edits[0].clear()
    bw._name_edits[1].clear()
    assert seen[-1] == (3, "")


def test_armed_sets_property():
    bw = BinWidget(0)
    bw.set_armed(True)
    assert bw.property("armed") == "true"
    bw.set_armed(False)
    assert bw.property("armed") == "false"


def test_image_api_preserved():
    bw = BinWidget(0)
    bw.add_image(5, None, "x.png")
    assert bw.image_ids() == [5]
    bw.remove_ids([5])
    assert bw.image_ids() == []


def test_bin_shell_paints():
    bw = BinWidget(0)
    bw.resize(280, 200)
    assert not bw.grab().isNull()
    bw.set_armed(True)
    assert not bw.grab().isNull()
    bw.set_flagged(True)
    assert not bw.grab().isNull()
