<div align="center">

<img src="https://raw.githubusercontent.com/SillySilk/AnimusSorter/civitai-assets/animus_sorter.png" alt="Animus Sorter" width="100%">

# Animus Sorter

### Sort & name your training images — the companion to **[AnimaForge](https://github.com/SillySilk/AnimaForge)**

[![License: MIT](https://img.shields.io/badge/License-MIT-d4af37.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)

**Turn a pile of scraped images into a clean, training-ready dataset in minutes.**
Sort here, then train in [AnimaForge](https://github.com/SillySilk/AnimaForge).

</div>

---

## ✨ How it works

Open a folder, sort each image into a subject **bin** with tactile one-key **"punch" presets** — one photo at a time, like sorting physical prints — and hit **Execute**. Every binned image is renamed and moved into a `sorted/` subfolder, with the filename encoding exactly who's in the picture.

The punch keys are **latching car-radio presets**: press a key to *arm* a bin (it lights amber, the others gray out), then click an image to fly it in. Or drag a tile straight into any bin.

## 🏷 The filename *is* the data

Animus Sorter renames files into the convention AnimaForge reads to derive trigger tokens automatically:

```
NAME_SERIAL_CATEGORY.png
```

```
Aria_001_Character.png            one subject
Aria-Garden_004_Character.png     two subjects (hyphen separates names)
Picnic basket_012_Object.png      spaces allowed inside a name
Morning-Evening_002_Style.png     works for any category
```

Load the `sorted/` folder into AnimaForge and your **Name Cast** pre-fills straight from the filenames — no find-and-replace across hundreds of caption files.

## 🖼 Feed it anything, get PNG back

The tray reads **jpg, jpeg, jfif, jpe, png, apng, gif, webp, bmp, tiff, tif, avif, heic, heif** — including iPhone photos and the AVIFs modern browsers save. On Execute, everything is **losslessly converted to PNG**: EXIF rotation baked in, transparency preserved, first frame of animations. One uniform format out, no matter what went in. Files that can't be decoded get an unmissable **UNREADABLE** reject tag in the tray.

## 🤖 Optional AI assist (local)

Point it at a running **[LM Studio](https://lmstudio.ai)** vision model and each bin gains **Analyze** (detect who's in the bin's images) and **Auto-sort tray** (file matching images in automatically — exactly-this-set, no outsiders). Entirely optional, entirely local; the app never touches the network otherwise. Auto-sorted images just land in bins — nothing is renamed until *you* hit Execute.

## ⚡ Quick start

```bat
pip install -r requirements.txt
run.bat
```

Requires **Python 3.11+** (Windows). Dependencies: PyQt6, Pillow (≥ 11.1), pillow-heif.

## 🧭 The workflow

1. **Open** a folder and pick the project category — **Characters**, **Objects**, or **Styles** (one per project).
2. **Name your bins** — one subject set per bin (`Aria`, or `Aria + Garden`).
3. **Sort** — arm a bin and click images in, or drag tiles. One image at a time.
4. **Execute** — every binned image is converted to PNG, renamed `NAME_SERIAL_CATEGORY.png`, and moved into `sorted/`.

Fully local. No network, no accounts, no uploads.

## 💛 Free & open source

100% free, MIT licensed. Install it, use it, sort as many datasets as you want.

---

<div align="center">

**Built for the Anima community — pairs with [AnimaForge](https://github.com/SillySilk/AnimaForge).** 🔥

</div>
