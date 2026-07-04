"""Headless guards for MainWindow redesign wiring (footer, audio, exec label)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from sorting_tray.audio import SoundController
from sorting_tray.fonts import load_fonts

_app = QApplication.instance() or QApplication([])
load_fonts()

from sorting_tray.mainwindow import MainWindow


def test_footer_and_sound_present():
    w = MainWindow()
    assert isinstance(w.sound, SoundController)
    footer = w.findChild(QWidget, "footerBar")
    assert footer is not None
    w.close()


def test_execute_label_dynamic():
    w = MainWindow()
    assert w.execute_btn.text().startswith("EXECUTE · 0 PRINTS · 0 BINS")
    w.close()


def test_sound_toggle_mutes():
    w = MainWindow()
    w.control.snd_toggle.setChecked(True)
    w.control._on_sound_toggle(True)
    assert w.sound.muted is True
    w.close()


def test_placeholder_is_reject_plate():
    from sorting_tray.loader import THUMB_BASE
    from sorting_tray.mainwindow import _placeholder_pixmap

    pm = _placeholder_pixmap()
    assert not pm.isNull()
    assert pm.width() == THUMB_BASE and pm.height() == THUMB_BASE
    img = pm.toImage()
    colors = {
        img.pixelColor(x, y).name()
        for x in range(0, img.width(), 16)
        for y in range(0, img.height(), 16)
    }
    # The old placeholder was one flat fill; the reject tag has plate, stripes,
    # and stamp ink.
    assert len(colors) > 3


def test_gallery_frame_status():
    w = MainWindow()
    assert w.gallery_frame is not None
    assert w.gallery.objectName() == "galleryList"
    w.gallery_frame.set_status("5 PRINTS UNSORTED", armed=False)
    assert "5 PRINTS" in w.gallery_frame.status.text()
    assert w.gallery.property("armed") == "false"
    w.gallery_frame.set_status("ARMED · BIN 2", armed=True)
    assert w.gallery.property("armed") == "true"
    w.close()
