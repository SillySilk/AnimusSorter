"""Qt style sheets. The 1950s radio punch keys are the signature visual."""

# App-wide base. Deliberately plain so the punch keys carry the character.
APP_QSS = """
QWidget {
    background: #2b2b2b;
    color: #e6e6e6;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}
QLabel#categoryIndicator {
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px 10px;
    background: #1e1e1e;
    font-weight: 600;
    letter-spacing: 1px;
}
QListWidget {
    background: #232323;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
}
QListWidget::item:selected {
    background: #3d5a80;
    border: 1px solid #98c1d9;
}
#binPanel { background: #262626; }
QGroupBox {
    border: 1px solid #444;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 6px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QGroupBox[flagged="true"] {
    border: 2px solid #e63946;
}
QGroupBox[armed="true"] {
    border: 2px solid #ffcc44;
    background: #2f2a1e;
}
QLabel#binHeader {
    font-family: "Segoe Script", "Brush Script MT", "Comic Sans MS", cursive;
    font-size: 24px;
    font-weight: 700;
    color: #ffd866;
    padding: 1px 4px 3px 4px;
}
QPushButton#executeButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3aaf5c, stop:1 #1f7a3d);
    border: 2px solid #145c2b;
    border-radius: 6px;
    padding: 12px 22px;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 2px;
}
QPushButton#executeButton:hover { background: #3fbf66; }
QPushButton#executeButton:pressed { background: #1f7a3d; }
"""

# The radio preset punch key. Heavy chrome bezel, brushed-metal face, and a
# strong pressed state that visibly depresses like a real mechanical button.
PUNCH_KEY_QSS = """
QPushButton#punchKey {
    color: #1a1a1a;
    font-size: 20px;
    font-weight: 800;
    min-width: 46px;
    min-height: 54px;
    border-top: 2px solid #f5f5f5;
    border-left: 2px solid #d8d8d8;
    border-right: 2px solid #6e6e6e;
    border-bottom: 4px solid #4a4a4a;
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fbfbfb, stop:0.45 #d0d0d0, stop:0.5 #b9b9b9, stop:1 #e2e2e2);
}
QPushButton#punchKey:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:0.45 #dcdcdc, stop:0.5 #c7c7c7, stop:1 #ececec);
}
QPushButton#punchKey:pressed,
QPushButton#punchKey:checked {
    color: #000000;
    /* Collapse the bottom bevel so the key sinks into the bezel. */
    border-top: 4px solid #4a4a4a;
    border-left: 2px solid #6e6e6e;
    border-right: 2px solid #d8d8d8;
    border-bottom: 2px solid #f5f5f5;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #9c9c9c, stop:0.5 #b4b4b4, stop:1 #cfcfcf);
    padding-top: 3px;
}
/* A latched (armed) preset glows amber to match its highlighted bin. */
QPushButton#punchKey:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #d6ad4e, stop:0.5 #e6c25f, stop:1 #d6ad4e);
    border-top: 4px solid #8a6d20;
}
/* The other presets go dark and inert while one bin is armed. */
QPushButton#punchKey:disabled {
    color: #5a5a5a;
    border-top: 2px solid #4f4f4f;
    border-left: 2px solid #444;
    border-right: 2px solid #383838;
    border-bottom: 4px solid #2b2b2b;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4a4a4a, stop:0.5 #3f3f3f, stop:1 #454545);
}
"""
