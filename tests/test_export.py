"""export_as_png: every source becomes a PNG at target; originals are deleted
only after a successful write; failures leave the source untouched."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PIL import Image

from sorting_tray.models import export_as_png  # noqa: E402


def test_jpeg_exif_orientation_baked(tmp_path):
    src = tmp_path / "a.jpg"
    img = Image.new("RGB", (40, 20), "red")
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 CW to display
    img.save(src, exif=exif)
    target = tmp_path / "out.png"
    export_as_png(src, target)
    assert not src.exists()
    with Image.open(target) as out:
        assert out.format == "PNG"
        assert out.size == (20, 40)  # rotation baked in


def test_palette_gif_first_frame_only(tmp_path):
    frames = [Image.new("P", (10, 10), i) for i in (1, 2)]
    src = tmp_path / "a.gif"
    frames[0].save(src, save_all=True, append_images=frames[1:])
    target = tmp_path / "out.png"
    export_as_png(src, target)
    with Image.open(target) as out:
        assert out.format == "PNG"
        assert out.mode in ("RGB", "RGBA")
        assert getattr(out, "n_frames", 1) == 1


def test_rgba_webp_alpha_preserved(tmp_path):
    src = tmp_path / "a.webp"
    Image.new("RGBA", (10, 10), (255, 0, 0, 128)).save(src, lossless=True)
    target = tmp_path / "out.png"
    export_as_png(src, target)
    with Image.open(target) as out:
        assert out.mode == "RGBA"
        assert out.getpixel((5, 5))[3] == 128


def test_png_renamed_byte_identical(tmp_path):
    src = tmp_path / "a.png"
    Image.new("RGB", (10, 10), "blue").save(src)
    original = src.read_bytes()
    target = tmp_path / "out.png"
    export_as_png(src, target)
    assert not src.exists()
    assert target.read_bytes() == original


@pytest.mark.parametrize("ext", [".avif", ".heic"])
def test_modern_formats_convert(tmp_path, ext):
    src = tmp_path / f"a{ext}"
    Image.new("RGB", (12, 12), "green").save(src)
    target = tmp_path / "out.png"
    export_as_png(src, target)
    assert not src.exists()
    with Image.open(target) as out:
        assert out.format == "PNG"
        assert out.size == (12, 12)


def test_failure_leaves_original_and_no_partial_target(tmp_path):
    src = tmp_path / "bad.jpg"
    src.write_bytes(b"this is not an image")
    target = tmp_path / "out.png"
    with pytest.raises(Exception):
        export_as_png(src, target)
    assert src.exists()
    assert not target.exists()
