"""Domain model and the filename logic that drives the whole app.

The output filename format is the heart of the project:

    NAME_SERIAL_CATEGORY.ext        e.g. Homer-Marge_004_Character.jpg

- NAME      one or more subject names joined by '-'. Spaces allowed inside a name.
- SERIAL    zero-padded 3-digit, per bin, starting at 001.
- CATEGORY  literal 'Character' | 'Object' | 'Style', locked at project open.
- ext       the original extension, preserved untouched.

The underscore is structural and never appears inside a field.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Category(str, Enum):
    CHARACTER = "Character"
    OBJECT = "Object"
    STYLE = "Style"


# Extensions Pillow/Qt decode reliably. Extension is preserved on rename; we
# never touch the bytes, only the name.
READABLE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif",
}

BIN_COUNT = 8
MAX_SUBJECTS_PER_BIN = 10


def build_filename(name_block: str, serial: int, category: str, ext: str) -> str:
    """Assemble a target filename.

    `ext` is the original extension *with* its leading dot (e.g. '.png').
    """
    return f"{name_block}_{serial:03d}_{category}{ext}"


def next_serial_start(folder: Path, name_block: str, category: str) -> int:
    """Highest existing serial for this name_block + category, plus one.

    Scans the folder for files already matching the exact
    `{name_block}_###_{category}.` pattern (case-insensitive) so re-runs
    continue past existing files instead of colliding. Returns 1 for a folder
    with no matches.
    """
    pattern = re.compile(
        rf"^{re.escape(name_block)}_(\d{{3}})_{re.escape(category)}\.",
        re.IGNORECASE,
    )
    highest = 0
    for f in folder.iterdir():
        m = pattern.match(f.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def name_has_hyphen(name: str) -> bool:
    """A single name box containing '-' reads as two subjects (Jean-Luc).

    The user is warned but not blocked.
    """
    return "-" in name.strip()


@dataclass
class ImageItem:
    """One image on disk. `location` is 'tray' or a bin index (0..7)."""

    path: Path
    location: object = "tray"  # "tray" | int(bin_index)

    @property
    def ext(self) -> str:
        return self.path.suffix

    @property
    def name(self) -> str:
        return self.path.name


@dataclass
class Bin:
    """One subject set. The name boxes are the only free-text the user types."""

    index: int
    subject_count: int = 1
    names: list[str] = field(default_factory=lambda: [""])
    image_ids: list[int] = field(default_factory=list)

    def name_block(self) -> str:
        return "-".join(n.strip() for n in self.names)

    def is_empty(self) -> bool:
        return not self.image_ids

    def names_filled(self) -> bool:
        """Every active name box must hold a non-blank value."""
        if len(self.names) < self.subject_count:
            return False
        return all(n.strip() for n in self.names[: self.subject_count])


@dataclass
class Project:
    folder_path: Path
    category: Category
    images: list[ImageItem] = field(default_factory=list)
    bins: list[Bin] = field(default_factory=list)

    @classmethod
    def open(cls, folder: Path, category: Category) -> "Project":
        bins = [Bin(index=i) for i in range(BIN_COUNT)]
        return cls(folder_path=folder, category=category, bins=bins)
