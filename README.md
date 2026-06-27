# Animus Sorter — sort & name your training images

A free, local Windows app that turns a pile of scraped images into a clean,
training-ready dataset in minutes. It's the companion to
[**AnimaForge**](https://github.com/SillySilk/AnimaForge): sort here, then train there.

You open a folder, sort each image into a subject **bin** with tactile one-key
"punch" presets (one photo at a time, like sorting physical prints), and hit
**Execute**. Every binned image is renamed and moved into a `sorted/` subfolder,
with the filename encoding exactly who's in the picture.

## The filename *is* the data

Animus Sorter renames files into the convention AnimaForge reads to derive trigger
tokens automatically:

```
NAME_SERIAL_CATEGORY.ext
```

```
Aria_001_Character.png            one subject
Aria-Garden_004_Character.jpg     two subjects (hyphen separates names)
Picnic basket_012_Object.png      spaces allowed inside a name
Morning-Evening_002_Style.gif     works for any category
```

- **NAME** — the subject(s). Multiple subjects join with a hyphen.
- **SERIAL** — a zero-padded count within the bin (`001`+).
- **CATEGORY** — `Character`, `Object`, or `Style`, set once when you open the project.

Load the `sorted/` folder into AnimaForge and your **Name Cast** pre-fills straight
from the filenames — no find-and-replace across hundreds of caption files.

## Quick start

```bat
pip install -r requirements.txt
run.bat
```

Requires **Python 3.11+** (Windows). Dependencies: PyQt6, Pillow.

## How it works

1. **Open** a folder of mixed images and pick the project category (Characters / Objects / Styles — one per project).
2. **Name your bins** — one subject set per bin (`Aria`, or `Aria + Garden`).
3. **Sort** — press a punch key to *arm* a bin (it latches; the others gray out), then click an image to fly it in. Or drag a tile into any bin. One image at a time.
4. **Execute** — every binned image is renamed `NAME_SERIAL_CATEGORY.ext` and moved into `sorted/`.

Fully local. No network, no accounts, no uploads.

## Free & open source

100% free. Install it, use it, sort as many datasets as you want.

Built for the Anima community — pairs with [AnimaForge](https://github.com/SillySilk/AnimaForge).
