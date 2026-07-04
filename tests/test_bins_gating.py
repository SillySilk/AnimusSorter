"""Headless gating tests for the per-bin Analyze button."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtWidgets import QApplication

from sorting_tray.bins import BinWidget, ANALYZE_MIN_IMAGES

_app = QApplication.instance() or QApplication([])


def _bin_with_images(category, n, name="Homer"):
    bw = BinWidget(0)
    bw.set_category_label(category)
    for i in range(n):
        bw.add_image(i, None, f"img{i}")
    if name is not None:
        bw._name_edits[0].setText(name)
    return bw


def test_disabled_without_enough_images():
    bw = _bin_with_images("Character", ANALYZE_MIN_IMAGES - 1)
    assert bw.analyze_enabled() is False


def test_disabled_with_blank_name():
    bw = _bin_with_images("Character", ANALYZE_MIN_IMAGES, name=None)
    assert bw.analyze_enabled() is False


def test_enabled_character_with_enough_named_images():
    bw = _bin_with_images("Character", ANALYZE_MIN_IMAGES)
    assert bw.analyze_enabled() is True


def test_enabled_for_object_too():
    bw = _bin_with_images("Object", ANALYZE_MIN_IMAGES)
    assert bw.analyze_enabled() is True


def test_disabled_for_style_category():
    bw = _bin_with_images("Style", ANALYZE_MIN_IMAGES)
    assert bw.analyze_enabled() is False


def test_autosort_locked_until_analyzed():
    bw = _bin_with_images("Character", ANALYZE_MIN_IMAGES)
    assert bw.autosort_enabled() is False
    bw.set_roster({"Homer": "bald yellow man"})
    assert bw.autosort_enabled() is True
