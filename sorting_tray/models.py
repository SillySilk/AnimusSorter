"""Domain model and the filename logic that drives the whole app.

The output filename format is the heart of the project:

    NAME_SERIAL_CATEGORY.ext        e.g. Homer-Marge_004_Character.png

- NAME      one or more subject names joined by '-'. Spaces allowed inside a name.
- SERIAL    zero-padded 3-digit, per bin, starting at 001.
- CATEGORY  literal 'Character' | 'Object' | 'Style', locked at project open.
- ext       always '.png' on output — export losslessly converts every source.

The underscore is structural and never appears inside a field.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

# HEIC/HEIF decode for every consumer of this module (loader, export, tests).
# Hard dependency — a missing pillow-heif fails loudly at import, per the
# no-fallbacks rule.
register_heif_opener()


class Category(str, Enum):
    CHARACTER = "Character"
    OBJECT = "Object"
    STYLE = "Style"


# Extensions Pillow (+ pillow-heif) decodes reliably for scraped/photo folders.
# Export converts everything to PNG, so odd input extensions cost nothing
# downstream. Deliberately excluded: .psd/.ico/.tga/.qoi and other exotica —
# not what scrapers or cameras produce.
READABLE_EXTENSIONS = {
    ".jpg", ".jpeg", ".jfif", ".jpe", ".png", ".apng", ".gif", ".webp",
    ".bmp", ".tiff", ".tif", ".avif", ".heic", ".heif",
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


def export_as_png(src: Path, target: Path) -> None:
    """Move `src` to `target`, converting to PNG when needed.

    Already-PNG sources are renamed byte-identically (no re-encode). Anything
    else is decoded with Pillow, EXIF orientation baked in, mode normalized
    (alpha preserved), first frame only for animated sources, then saved as a
    PNG carrying the source ICC profile. `src` is deleted only after `target`
    is written successfully; on any failure `src` is left untouched and a
    partially written `target` is removed.
    """
    if src.suffix.lower() == ".png":
        src.rename(target)
        return
    try:
        with Image.open(src) as img:
            icc = img.info.get("icc_profile")
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "RGBA"):
                has_alpha = img.mode in ("LA", "PA") or "transparency" in img.info
                img = img.convert("RGBA" if has_alpha else "RGB")
            kwargs = {"icc_profile": icc} if icc else {}
            img.save(target, format="PNG", **kwargs)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    src.unlink()


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
