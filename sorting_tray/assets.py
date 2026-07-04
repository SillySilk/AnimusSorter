"""Locate bundled assets; render recolorable single-color SVG icons.

The forge clip-art SVGs use ``fill="currentColor"`` so a single string swap
recolors them per placement (brass, ink, ember, ...) before rasterizing.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_ASSET_DIR = Path(__file__).resolve().parent / "assets"


def asset_path(*parts: str) -> Path:
    """Absolute path under ``sorting_tray/assets/``."""
    return _ASSET_DIR.joinpath(*parts)


def load_svg_pixmap(name: str, color: str = "#000000", size: int = 64) -> QPixmap:
    """Render ``svg/<name>.svg`` recolored to ``color`` at ``size`` px square."""
    path = asset_path("svg", f"{name}.svg")
    data = path.read_text(encoding="utf-8").replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(data.encode("utf-8")))
    pm = QPixmap(QSize(size, size))
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm


def load_svg_icon(name: str, color: str = "#000000", size: int = 64) -> QIcon:
    return QIcon(load_svg_pixmap(name, color, size))
