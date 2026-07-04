"""Qt style sheets — the industrial blacksmith re-skin.

Palette: blackened steel + raw iron chassis, brass control hardware, aged-copper
bin name plates, forge-ember heat accents used only for "hot"/active states. The
mechanical preset keys carry the most character (see PUNCH_KEY_QSS); custom paint
in controlbar.py/bins.py/gallery.py layers on top of this flat QSS base.

Exact tokens come from the handoff README "Design Tokens" section.
"""

# ---------------------------------------------------------------------------
# App-wide base stylesheet.
# ---------------------------------------------------------------------------
APP_QSS = """
QWidget {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #211d19, stop:1 #15120f);
    color: #e6dccb;
    font-family: "Zilla Slab", "Georgia", serif;
    font-size: 13px;
}

/* --- Control bar faceplate ------------------------------------------------ */
QWidget#controlBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #262119, stop:1 #1b1714);
    border: 1px solid #0a0807;
    border-radius: 5px;
}
QWidget#radioBezel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #100d0b, stop:1 #181512);
    border: 1px solid #0a0807;
    border-radius: 5px;
}
QLabel#forgeBadge {
    background: qradialgradient(cx:0.4, cy:0.35, radius:0.8,
        stop:0 #d8b25a, stop:0.6 #9c7a32, stop:1 #5e451f);
    border: 2px solid #3a2a10;
    border-radius: 21px;
}
QLabel#brandWordmark { color: #cf965d; }
QLabel#brandSubtitle {
    color: #b88a5a;
    font-family: "Zilla Slab";
    font-weight: 700;
    font-size: 9px;
    letter-spacing: 2px;
}
QLabel#sectionLabel {
    color: #5c5446;
    font-family: "DM Mono", "Consolas", monospace;
    font-size: 9px;
    letter-spacing: 2px;
}
QLabel#radioTitle {
    color: #b88a3c;
    font-family: "DM Mono", "Consolas", monospace;
    font-size: 9px;
    letter-spacing: 2px;
}

/* --- Category brass plate ------------------------------------------------- */
QLabel#categoryIndicator {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #cda657, stop:0.55 #9c7a32, stop:1 #7a5c28);
    border: 1px solid #5e451f;
    border-radius: 3px;
    padding: 5px 12px;
    color: #241806;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 2px;
}

/* --- Buttons (open + generic) -------------------------------------------- */
QPushButton#openButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2e2925, stop:1 #1d1916);
    border: 1px solid #0a0807;
    border-radius: 4px;
    padding: 8px 16px;
    color: #cabfae;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.8px;
}
QPushButton#openButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3a342d, stop:1 #24201b);
    color: #ece3d2;
}
QPushButton#openButton:pressed {
    background: #1a1613;
}

/* --- Sort dropdown -------------------------------------------------------- */
QComboBox {
    background: #15120f;
    border: 1px solid #0a0807;
    border-radius: 3px;
    padding: 4px 8px;
    color: #cabfae;
    font-size: 12px;
}
QComboBox:hover { border: 1px solid #5e451f; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #15120f;
    border: 1px solid #5e451f;
    color: #cabfae;
    selection-background-color: #5e451f;
    selection-color: #ece3d2;
}

/* --- Thumb-size slider (brass handle) ------------------------------------ */
QSlider::groove:horizontal {
    height: 4px;
    background: #0a0807;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #cda657, stop:1 #9c7a32);
    border: 1px solid #5e451f;
    width: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #d8b25a; }

/* --- Gallery / sorting tray cavity --------------------------------------- */
QListWidget {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0e0c0a, stop:1 #16130f);
    border: 1px solid #060504;
    border-radius: 4px;
    color: #cabfae;
}
QListWidget::item {
    border: 1px solid #0b0908;
    border-radius: 2px;
    color: #cabfae;
}
QListWidget::item:selected {
    border: 1px solid #b88a3c;
    background: rgba(184, 138, 60, 0.18);
}
/* While a bin is armed, the tray tiles invite the click. */
QListWidget#galleryList[armed="true"]::item {
    border: 1px solid rgba(255, 120, 40, 0.55);
}

/* --- Bin panel + bins ----------------------------------------------------- */
QWidget#binPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #211d19, stop:1 #15120f);
}
/* The bins live in a scroll area; keep its viewport on-palette and frameless. */
QScrollArea#binsScroll, QScrollArea#binsScroll > QWidget > QWidget {
    background: transparent;
    border: none;
}
/* The tapered steel shell + armed/flagged ring are drawn in BinWidget.paintEvent;
   keep the QSS box itself transparent so no rectangular fill leaks behind it. */
QGroupBox#binWidget {
    background: transparent;
    border: none;
}

/* Bin auto-name title (was a script font; now bone slab).
   NOTE: font-family/size/weight are owned in code by FitLabel so the banner can
   auto-shrink long names — a QSS font-size here would override setFont. */
QLabel#binHeader {
    color: #ece3d2;
    padding: 1px 4px;
}
QLabel#binHeader[armed="true"] { color: #ffce9a; }

/* Bin number tab (stamped steel plate). */
QLabel#binNumberTab {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3a352e, stop:1 #1c1813);
    border: 1px solid #0a0807;
    border-radius: 3px;
    color: #cabfae;
    font-family: "Zilla Slab";
    font-weight: 700;
    font-size: 13px;
    padding: 1px 7px;
}
QLabel#binNumberTab[armed="true"] { color: #ffb878; }

/* Mechanical tally counter window. */
QLabel#binTally {
    background: #0e0c0a;
    border: 1px solid #050403;
    border-radius: 2px;
    color: #6a6256;
    font-family: "DM Mono", monospace;
    font-size: 14px;
    padding: 1px 6px;
}
QLabel#binTally[hot="true"] { color: #ff9a4d; }

/* Drop window (the strip). */
QListWidget#dropStrip {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0e0c0a, stop:1 #16130f);
    border: 1px dashed rgba(132, 120, 98, 0.22);
    border-radius: 2px;
}
QListWidget#dropStrip[armed="true"] {
    border: 1px dashed rgba(255, 140, 60, 0.55);
}

/* Subject stepper buttons + count window. */
QPushButton#stepperButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5e564c, stop:1 #322c25);
    border: 1px solid #0a0807;
    border-bottom: 2px solid #1c1813;
    border-radius: 3px;
    color: #e6dccb;
    font-weight: 700;
    font-size: 13px;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
}
QPushButton#stepperButton:pressed {
    border-top: 2px solid #1c1813;
    border-bottom: 1px solid #0a0807;
    padding-top: 1px;
}
QLabel#stepperCount {
    background: #0e0c0a;
    border: 1px solid #050403;
    border-radius: 2px;
    color: #cabfae;
    font-family: "DM Mono", monospace;
    font-size: 13px;
    padding: 1px 8px;
}
QLabel#filenamePreview {
    color: #7a6a48;
    font-family: "DM Mono", monospace;
    font-size: 9px;
}
QLabel#subjLabel {
    color: #8a8176;
    font-family: "DM Mono", monospace;
    font-size: 8px;
    letter-spacing: 2px;
}

/* Copper name plate hosting the editable name fields. */
QWidget#copperPlate {
    background: qlineargradient(x1:0, y1:0, x2:0.6, y2:1,
        stop:0 #c2844f, stop:0.48 #9a5a36, stop:1 #7a4226);
    border: 1px solid #3a2414;
    border-radius: 3px;
}
QWidget#copperPlate QLineEdit {
    background: transparent;
    border: none;
    color: #2c1608;
    font-family: "Zilla Slab";
    font-size: 14px;
    padding: 2px 4px;
}
QWidget#copperPlate QLineEdit::placeholder { color: rgba(44, 22, 8, 0.45); }

/* --- Execute (ember) ----------------------------------------------------- */
QPushButton#executeButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #e2581f, stop:0.55 #c23d0c, stop:1 #9c2f08);
    border: 1px solid #5a1f06;
    border-bottom: 3px solid #4a1804;
    border-radius: 4px;
    padding: 10px 20px;
    color: #1a0a04;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 2px;
}
QPushButton#executeButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #f56a2c, stop:0.55 #d4470f, stop:1 #a8350a);
}
QPushButton#executeButton:pressed {
    border-bottom: 1px solid #4a1804;
    padding-top: 12px;
}
QPushButton#executeButton:disabled {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4a443b, stop:1 #2a251f);
    border: 1px solid #1c1813;
    border-bottom: 3px solid #14110e;
    color: #6a6256;
}

/* --- AI assist buttons (per bin) + settings gear ------------------------- */
QPushButton#analyzeButton, QPushButton#autosortButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2e2925, stop:1 #1d1916);
    border: 1px solid #0a0807;
    border-bottom: 2px solid #14110e;
    border-radius: 3px;
    padding: 4px 8px;
    color: #cabfae;
    font-family: "DM Mono", monospace;
    font-size: 10px;
    letter-spacing: 1px;
}
QPushButton#analyzeButton:hover, QPushButton#autosortButton:hover {
    border: 1px solid #5e451f;
    border-bottom: 2px solid #14110e;
    color: #ece3d2;
}
QPushButton#analyzeButton:enabled { color: #cda657; }
QPushButton#autosortButton:enabled { color: #ff9a4d; }
QPushButton#analyzeButton:disabled, QPushButton#autosortButton:disabled {
    background: #1a1613;
    border: 1px solid #14110e;
    color: #5c5446;
}
QPushButton#settingsButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2e2925, stop:1 #1d1916);
    border: 1px solid #0a0807;
    border-radius: 4px;
    color: #b88a3c;
    font-family: "DM Mono", monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
QPushButton#settingsButton:hover { border: 1px solid #5e451f; color: #ece3d2; }

/* --- SND mute toggle ----------------------------------------------------- */
QPushButton#sndToggle {
    background: #15120f;
    border: 1px solid #0a0807;
    border-radius: 3px;
    color: #b88a3c;
    font-family: "DM Mono", monospace;
    font-size: 8px;
    letter-spacing: 1px;
    padding: 2px 6px;
}
QPushButton#sndToggle:checked { color: #6a6256; }

/* --- Footer -------------------------------------------------------------- */
QWidget#footerBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1c1815, stop:1 #14110e);
    border-top: 1px solid #0a0807;
}
QLabel#footerText {
    color: #6f665a;
    font-family: "DM Mono", monospace;
    font-size: 9px;
    letter-spacing: 2px;
}

/* --- Gallery stamped header ---------------------------------------------- */
/* The metal shell + rivets are painted in GalleryFrame.paintEvent (shared with
   the bins), so keep the QSS box transparent — a fill here would cover it. */
QWidget#galleryFrame {
    background: transparent;
    border: none;
}
QLabel#galleryStatus {
    color: #8a8176;
    font-family: "DM Mono", monospace;
    font-size: 11px;
    letter-spacing: 1px;
}
QLabel#galleryStatus[armed="true"] { color: #ff9a4d; }

/* --- Scrollbars ---------------------------------------------------------- */
QScrollBar:vertical { background: #0c0a08; width: 8px; margin: 0; }
QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4a443b, stop:1 #2a251f);
    border: 1px solid #0a0807;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: #0c0a08; height: 8px; margin: 0; }
QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4a443b, stop:1 #2a251f);
    border: 1px solid #0a0807;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* --- Dialogs / message boxes share the chassis look --------------------- */
QMessageBox, QDialog { background: #1b1714; }
QMessageBox QLabel, QDialog QLabel { color: #e6dccb; }
"""

# ---------------------------------------------------------------------------
# The radio preset punch key — QSS fallback (depress simulation + ember latch).
# Phase 4 swaps in a custom-painted PunchKey for vertical travel + knurl + glow,
# but this keeps the keys mechanical and on-palette until then.
# ---------------------------------------------------------------------------
PUNCH_KEY_QSS = """
QPushButton#punchKey {
    color: #e6dccb;
    font-family: "Zilla Slab";
    font-size: 15px;
    font-weight: 700;
    min-width: 30px;
    min-height: 44px;
    border-top: 2px solid #7c746a;
    border-left: 2px solid #4a443b;
    border-right: 2px solid #1c1813;
    border-bottom: 4px solid #100d0b;
    border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2a2620, stop:0.5 #7c746a, stop:1 #26221d);
}
QPushButton#punchKey:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #322d26, stop:0.5 #8a8176, stop:1 #2e2a24);
}
QPushButton#punchKey:pressed,
QPushButton#punchKey:checked {
    color: #1a0c04;
    border-top: 4px solid #5a1f06;
    border-left: 2px solid #1c1813;
    border-right: 2px solid #4a443b;
    border-bottom: 2px solid #7c746a;
    padding-top: 3px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ff7a2a, stop:1 #c23d0c);
}
QPushButton#punchKey:disabled {
    color: #4a443b;
    border-top: 2px solid #2a251f;
    border-left: 2px solid #1c1813;
    border-right: 2px solid #14110e;
    border-bottom: 4px solid #100d0b;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #26221d, stop:0.5 #34302a, stop:1 #232019);
}
"""
