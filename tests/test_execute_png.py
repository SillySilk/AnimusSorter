"""Execute writes .png for every source format and deletes the originals."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from PyQt6.QtWidgets import QApplication

from sorting_tray.fonts import load_fonts

_app = QApplication.instance() or QApplication([])
load_fonts()

from sorting_tray.mainwindow import MainWindow  # noqa: E402
from sorting_tray.models import Category, ImageItem, Project  # noqa: E402


def test_rename_converts_everything_to_png(tmp_path):
    jpg = tmp_path / "photo.jpg"
    Image.new("RGB", (16, 16), "red").save(jpg)
    png = tmp_path / "already.png"
    Image.new("RGB", (16, 16), "blue").save(png)
    webp = tmp_path / "modern.webp"
    Image.new("RGBA", (16, 16), (0, 255, 0, 200)).save(webp)

    w = MainWindow()
    w.project = Project.open(tmp_path, Category.CHARACTER)
    w.project.images = [ImageItem(path=p) for p in (jpg, png, webp)]
    active = [(w.bins.bins[0], [0, 1, 2], "Homer")]

    renamed, errors = w._rename(active, tmp_path, Category.CHARACTER)
    w.close()

    assert renamed == 3
    assert errors == []
    produced = sorted(p.name for p in (tmp_path / "sorted").iterdir())
    assert produced == [
        "Homer_001_Character.png",
        "Homer_002_Character.png",
        "Homer_003_Character.png",
    ]
    assert not jpg.exists() and not png.exists() and not webp.exists()
    for p in (tmp_path / "sorted").iterdir():
        with Image.open(p) as img:
            assert img.format == "PNG"


def test_rename_failure_reports_error_and_keeps_original(tmp_path):
    bad = tmp_path / "corrupt.jpg"
    bad.write_bytes(b"junk")

    w = MainWindow()
    w.project = Project.open(tmp_path, Category.CHARACTER)
    w.project.images = [ImageItem(path=bad)]
    active = [(w.bins.bins[0], [0], "Homer")]

    renamed, errors = w._rename(active, tmp_path, Category.CHARACTER)
    w.close()

    assert renamed == 0
    assert len(errors) == 1 and "corrupt.jpg" in errors[0]
    assert bad.exists()
