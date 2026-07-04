"""Headless guards for the key SFX and SoundController mute gate."""

import os
import wave

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from sorting_tray import audio

_app = QApplication.instance() or QApplication([])


def test_wavs_valid():
    d = Path(__file__).resolve().parents[1] / "sorting_tray" / "assets" / "audio"
    for fn in ("push.wav", "release.wav"):
        with wave.open(str(d / fn)) as w:
            assert w.getnframes() > 0


def test_controller_mute_gates():
    sc = audio.SoundController()
    sc.set_muted(True)
    assert sc.muted is True
    sc.play_push()
    sc.play_release()  # must not raise
    sc.set_muted(False)
    assert sc.muted is False
