"""Headless guards for the restructured control bar."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton

from sorting_tray.controlbar import ControlBar, PunchKey

_app = QApplication.instance() or QApplication([])


def test_punchkey_travel_property_and_paint():
    pk = PunchKey(3)
    assert pk.text() == "3"
    pk.travel = 0.5
    assert abs(pk.travel - 0.5) < 1e-6
    pk.setChecked(True)
    assert pk._anim.endValue() == 1.0
    pk.setChecked(False)
    assert pk._anim.endValue() == 0.0
    assert not pk.grab().isNull()


def test_controlbar_uses_punchkeys():
    cb = ControlBar()
    assert all(isinstance(k, PunchKey) for k in cb.punch_keys)


def test_set_key_label_sets_name_and_tooltip():
    cb = ControlBar()
    cb.set_key_label(2, "Aria")
    assert cb.punch_keys[2].name() == "Aria"
    assert "Aria" in cb.punch_keys[2].toolTip()
    cb.set_key_label(2, "")
    assert cb.punch_keys[2].name() == ""


def test_has_sound_toggled_signal():
    cb = ControlBar()
    received = []
    cb.sound_toggled.connect(received.append)
    cb.snd_toggle.setChecked(True)  # checked == muted
    cb.snd_toggle.clicked.emit(True)
    assert received and received[-1] is True


def test_mount_execute_reparents_button():
    cb = ControlBar()
    btn = QPushButton("EXEC")
    cb.mount_execute(btn)
    # The button now lives inside the control bar's widget tree.
    parent = btn.parent()
    found = False
    while parent is not None:
        if parent is cb:
            found = True
            break
        parent = parent.parent()
    assert found


def test_interlock_preserved():
    cb = ControlBar()
    emitted = []
    cb.armed_changed.connect(emitted.append)
    cb._on_key(2)
    assert cb._armed == 2 and emitted[-1] == 2
    # Only the armed key stays enabled.
    assert cb.punch_keys[2].isEnabled()
    assert not cb.punch_keys[0].isEnabled()
    cb._on_key(2)  # release
    assert cb._armed == -1 and emitted[-1] == -1
    assert all(k.isEnabled() for k in cb.punch_keys)
