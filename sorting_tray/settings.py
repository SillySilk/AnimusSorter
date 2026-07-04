"""Standalone JSON settings for Animus Sorter (the LM Studio connection).

Self-contained — no dependency on AnimaForge. Pure load/save (no Qt) so it unit-tests
cleanly; the Qt SettingsDialog (in analysis_ui.py) edits an instance of this.
"""
from __future__ import annotations

import json
from pathlib import Path

from .llm import DEFAULT_MODEL, DEFAULT_URL


def default_path() -> Path:
    return Path.home() / ".animus_sorter" / "settings.json"


class Settings:
    DEFAULTS = {
        "lmstudio_url": DEFAULT_URL,
        # Blank == use whatever model LM Studio currently has loaded.
        "lmstudio_model": DEFAULT_MODEL,
    }

    def __init__(self, path: Path | None = None, data: dict | None = None):
        self.path = Path(path) if path else default_path()
        self._data = dict(self.DEFAULTS)
        if data:
            self._data.update({k: v for k, v in data.items() if k in self.DEFAULTS})

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        p = Path(path) if path else default_path()
        data = {}
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}  # corrupt/unreadable -> defaults
        return cls(p, data if isinstance(data, dict) else {})

    def get(self, key: str):
        return self._data.get(key, self.DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        if key in self.DEFAULTS:
            self._data[key] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
