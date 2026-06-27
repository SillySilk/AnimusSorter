"""Tests for the correctness-critical filename core."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sorting_tray.models import (  # noqa: E402
    Bin,
    build_filename,
    name_has_hyphen,
    next_serial_start,
)


def test_build_filename_single_subject():
    assert build_filename("Yogi bear", 1, "Character", ".png") == "Yogi bear_001_Character.png"


def test_build_filename_multi_subject_and_padding():
    assert build_filename("Homer-Marge-Lisa", 42, "Character", ".webp") == (
        "Homer-Marge-Lisa_042_Character.webp"
    )


def test_bin_name_block_joins_and_strips():
    b = Bin(index=0, subject_count=2, names=[" Homer ", "Marge"])
    assert b.name_block() == "Homer-Marge"


def test_next_serial_empty_folder(tmp_path):
    assert next_serial_start(tmp_path, "Homer", "Character") == 1


def test_next_serial_continues_past_existing(tmp_path):
    for n in (1, 2, 5):
        (tmp_path / f"Homer_{n:03d}_Character.png").write_bytes(b"x")
    # Different name_block or category must not interfere.
    (tmp_path / "Marge_009_Character.png").write_bytes(b"x")
    (tmp_path / "Homer_009_Object.png").write_bytes(b"x")
    assert next_serial_start(tmp_path, "Homer", "Character") == 6


def test_next_serial_case_insensitive(tmp_path):
    (tmp_path / "homer_003_character.png").write_bytes(b"x")
    assert next_serial_start(tmp_path, "Homer", "Character") == 4


def test_name_has_hyphen_warning():
    assert name_has_hyphen("Jean-Luc")
    assert not name_has_hyphen("Homer")


def test_bin_validation():
    full = Bin(index=0, subject_count=2, names=["Homer", "Marge"], image_ids=[1])
    assert full.names_filled()
    missing = Bin(index=1, subject_count=2, names=["Homer", ""], image_ids=[1])
    assert not missing.names_filled()
