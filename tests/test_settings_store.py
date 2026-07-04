"""Tests for the standalone JSON settings store."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sorting_tray.settings import Settings
from sorting_tray.llm import DEFAULT_MODEL, DEFAULT_URL


def test_defaults_when_no_file(tmp_path):
    s = Settings.load(tmp_path / "nope.json")
    assert s.get("lmstudio_url") == DEFAULT_URL
    assert s.get("lmstudio_model") == DEFAULT_MODEL


def test_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings.load(path)
    s.set("lmstudio_url", "http://host:9/v1")
    s.set("lmstudio_model", "my-vlm")
    s.save()
    again = Settings.load(path)
    assert again.get("lmstudio_url") == "http://host:9/v1"
    assert again.get("lmstudio_model") == "my-vlm"


def test_blank_model_is_allowed(tmp_path):
    path = tmp_path / "settings.json"
    s = Settings.load(path)
    s.set("lmstudio_model", "")   # blank == use whatever LM Studio has loaded
    s.save()
    assert Settings.load(path).get("lmstudio_model") == ""


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ not json", encoding="utf-8")
    s = Settings.load(path)
    assert s.get("lmstudio_url") == DEFAULT_URL
