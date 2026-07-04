"""Headless guards for the redesign asset infrastructure (fonts, SVG)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from sorting_tray import assets, fonts

_app = QApplication.instance() or QApplication([])


def test_font_files_present():
    d = Path(__file__).resolve().parents[1] / "sorting_tray" / "assets" / "fonts"
    names = {p.name for p in d.glob("*.ttf")}
    assert {
        "Ultra-Regular.ttf",
        "AlfaSlabOne-Regular.ttf",
        "ZillaSlab-Regular.ttf",
        "DMMono-Regular.ttf",
    } <= names


def test_load_fonts_registers_families():
    fam = fonts.load_fonts()
    assert fam["ui"] and fam["mono"] and fam["slab"] and fam["ultra"]


def test_svgs_present_and_load():
    for name in ("anvil", "hammer", "flame", "horseshoe", "hexbolt", "speaker"):
        assert assets.asset_path("svg", f"{name}.svg").exists()
        pm = assets.load_svg_pixmap(name, "#b88a3c", 32)
        assert not pm.isNull() and pm.width() == 32


def test_mainwindow_builds():
    fonts.load_fonts()
    from sorting_tray.mainwindow import MainWindow

    w = MainWindow()
    assert w.styleSheet()
    w.close()
