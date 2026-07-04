"""Mechanical key SFX via QSoundEffect, with a mute gate.

The arm/disarm path calls play_push()/play_release(); a SND ON/OFF toggle in the
radio header flips ``muted``. Missing WAVs degrade to silent no-ops.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QSoundEffect

from .applog import get_logger
from .assets import asset_path

log = get_logger("audio")


class SoundController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.muted = False
        self._push = self._load("push.wav")
        self._release = self._load("release.wav")

    def _load(self, fn: str) -> QSoundEffect | None:
        path = asset_path("audio", fn)
        if not path.exists():
            log.warning("missing sound: %s", path)
            return None
        eff = QSoundEffect(self)
        eff.setSource(QUrl.fromLocalFile(str(path)))
        eff.setVolume(0.75)
        return eff

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)
        log.debug("sound muted=%s", self.muted)

    def play_push(self) -> None:
        if not self.muted and self._push is not None:
            self._push.play()

    def play_release(self) -> None:
        if not self.muted and self._release is not None:
            self._release.play()
