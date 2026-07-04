"""Register bundled TTFs so the design's typography is available offline.

The industrial redesign leans on four specific families; we ship the TTFs and
register them with QFontDatabase at startup rather than trusting system fonts.
Each role falls back to a close system font if its file is missing.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QFontDatabase

from .applog import get_logger

log = get_logger("fonts")

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

# role -> (filenames to load, expected family, system fallback)
_ROLES = {
    "ultra": (["Ultra-Regular.ttf"], "Ultra", "Impact"),
    "slab": (["AlfaSlabOne-Regular.ttf"], "Alfa Slab One", "Rockwell"),
    "ui": (
        [
            "ZillaSlab-Regular.ttf",
            "ZillaSlab-Medium.ttf",
            "ZillaSlab-SemiBold.ttf",
            "ZillaSlab-Bold.ttf",
        ],
        "Zilla Slab",
        "Georgia",
    ),
    "mono": (["DMMono-Regular.ttf", "DMMono-Medium.ttf"], "DM Mono", "Consolas"),
}


def load_fonts() -> dict[str, str]:
    """Register every bundled face and return a role -> family-name map.

    Safe to call once after the QApplication exists. Missing or unreadable
    files are logged and skipped; the role then resolves to its fallback so
    the app still starts (and the QSS still has a usable family name).
    """
    resolved: dict[str, str] = {}
    for role, (files, _expected, fallback) in _ROLES.items():
        family: str | None = None
        for fn in files:
            path = _FONT_DIR / fn
            if not path.exists():
                log.warning("font missing: %s", path)
                continue
            fid = QFontDatabase.addApplicationFont(str(path))
            if fid < 0:
                log.warning("failed to register font: %s", path)
                continue
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                family = fams[0]
        resolved[role] = family or fallback
        log.info("font role %s -> %s", role, resolved[role])
    return resolved
