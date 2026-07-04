"""Dialogs for the AI assist: confirm detected characters, and edit LM Studio settings."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

BACKGROUND = "Background / extra"
IGNORE = "Ignore"


class ConfirmCharactersDialog(QDialog):
    """One row per detected figure: a thumbnail + a dropdown to label it (a named
    subject, Background/extra, or Ignore). OK unlocks only when every named subject is
    mapped to exactly one figure, so Auto-sort always has a profile for each name."""

    def __init__(self, figures_with_thumbs, subject_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm detected characters")
        self._subject_names = list(subject_names)
        self._descriptions = [desc for desc, _pm in figures_with_thumbs]
        self._combos: list[QComboBox] = []

        col = QVBoxLayout(self)
        intro = QLabel(
            "The model found these figures. Tell it which named subject each one is — "
            "every name must be assigned before you can continue."
        )
        intro.setWordWrap(True)
        col.addWidget(intro)

        choices = [""] + self._subject_names + [BACKGROUND, IGNORE]
        for desc, pm in figures_with_thumbs:
            row = QHBoxLayout()
            thumb = QLabel()
            thumb.setFixedSize(72, 72)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if pm is not None and not pm.isNull():
                thumb.setPixmap(pm.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
            else:
                thumb.setText("—")
            row.addWidget(thumb)

            label = QLabel(desc or "(no description)")
            label.setWordWrap(True)
            row.addWidget(label, 1)

            combo = QComboBox()
            combo.addItems(choices)
            combo.currentIndexChanged.connect(self._validate)
            combo.setFixedWidth(170)
            row.addWidget(combo)
            self._combos.append(combo)

            holder = QWidget()
            holder.setLayout(row)
            col.addWidget(holder)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        col.addWidget(self._buttons)
        self._validate()

    def _assigned_names(self) -> list[str]:
        return [c.currentText() for c in self._combos if c.currentText() in self._subject_names]

    def _validate(self) -> None:
        assigned = self._assigned_names()
        # Every named subject must be present exactly once across the combos.
        ok = sorted(assigned) == sorted(self._subject_names) and len(set(assigned)) == len(assigned)
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    def result_roster(self) -> dict:
        """{subject name -> the description of the figure mapped to it}."""
        roster = {}
        for combo, desc in zip(self._combos, self._descriptions):
            name = combo.currentText()
            if name in self._subject_names:
                roster[name] = desc
        return roster


class SettingsDialog(QDialog):
    """Edit the LM Studio URL + model and persist them."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LM Studio settings")
        self._settings = settings

        form = QFormLayout(self)
        self._url_edit = QLineEdit(settings.get("lmstudio_url"))
        self._url_edit.setMinimumWidth(320)
        form.addRow("Server URL", self._url_edit)
        self._model_edit = QLineEdit(settings.get("lmstudio_model"))
        self._model_edit.setPlaceholderText("blank = use whatever model is loaded")
        form.addRow("Vision model", self._model_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _on_save(self) -> None:
        self._settings.set("lmstudio_url", self._url_edit.text().strip() or self._settings.get("lmstudio_url"))
        self._settings.set("lmstudio_model", self._model_edit.text().strip())
        self._settings.save()
        self.accept()
