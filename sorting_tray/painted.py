"""Engraved / debossed / stamped text labels.

Qt Style Sheets have no ``text-shadow``, so the design's debossed wordmark and
the pressed-ink factory stamp are drawn by hand: the text is painted twice — a
dark (or light) offset copy behind, then the fill on top — to fake the bevel.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QLabel, QWidget


def draw_tray_shell(
    p: QPainter,
    w: int,
    h: int,
    *,
    armed: bool = False,
    flagged: bool = False,
    rim: bool = True,
) -> None:
    """Paint a square, shallow riveted parts-tray shell filling ``w`` x ``h``.

    Shared by the bins and the big gallery tray so they read as the same kind of
    object — flat sheet-metal trays with crisp 90° corners, an inner rim wall and
    a rivet at each corner — only the size differs. (The radio look is reserved
    for the eight preset keys; trays never get it.)
    """
    body = QRectF(1.5, 1.5, w - 3, h - 3)
    path = QPainterPath()
    path.addRect(body)

    grad = QLinearGradient(0, 0, w, h)
    if armed:
        grad.setColorAt(0.0, QColor("#7a6a52"))
        grad.setColorAt(0.30, QColor("#52443a"))
        grad.setColorAt(0.65, QColor("#3a2e25"))
        grad.setColorAt(1.0, QColor("#281d16"))
    else:
        grad.setColorAt(0.0, QColor("#6e665b"))
        grad.setColorAt(0.30, QColor("#48433c"))
        grad.setColorAt(0.65, QColor("#322e29"))
        grad.setColorAt(1.0, QColor("#23201c"))
    p.setBrush(grad)
    border = QColor("#e2581f") if (armed or flagged) else QColor("#0a0807")
    p.setPen(QPen(border, 2))
    p.drawPath(path)

    if rim:
        # Inner rim line — reads as the raised wall of a shallow tray.
        p.setPen(QPen(QColor(0, 0, 0, 90), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(6.5, 6.5, w - 13, h - 13))

    # Rivets inboard of each square corner.
    for rx, ry in ((11, 11), (w - 11, 11), (11, h - 11), (w - 11, h - 11)):
        rivet = QRadialGradient(rx, ry, 4)
        rivet.setColorAt(0.0, QColor("#8a8176"))
        rivet.setColorAt(0.6, QColor("#3a352f"))
        rivet.setColorAt(1.0, QColor("#15120f"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(rivet)
        p.drawEllipse(QRectF(rx - 3.5, ry - 3.5, 7, 7))


class _BaseTextLabel(QLabel):
    """Shared geometry: size to the text in the given font, repaint on change."""

    def __init__(self, text: str, font: QFont, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setFont(font)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._pad = 4

    def setText(self, text: str) -> None:  # type: ignore[override]
        super().setText(text)
        self.updateGeometry()
        self.update()

    def sizeHint(self):  # type: ignore[override]
        fm = QFontMetrics(self.font())
        rect = fm.boundingRect(self.text())
        return rect.adjusted(0, 0, self._pad * 2, self._pad * 2).size()

    def minimumSizeHint(self):  # type: ignore[override]
        return self.sizeHint()


class DebossedLabel(_BaseTextLabel):
    """Text with a 1px dark shadow behind it — looks pressed/engraved into metal."""

    def __init__(
        self,
        text: str,
        font: QFont,
        fill_color: str,
        shadow_color: str = "#0a0807",
        offset: int = 1,
        parent: QWidget | None = None,
    ):
        super().__init__(text, font, parent)
        self._fill = QColor(fill_color)
        self._shadow = QColor(shadow_color)
        self._offset = offset

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(self.font())
        rect = self.rect()
        painter.setPen(self._shadow)
        painter.drawText(rect.translated(self._offset, self._offset),
                         Qt.AlignmentFlag.AlignCenter, self.text())
        painter.setPen(self._fill)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()


class StampedLabel(_BaseTextLabel):
    """Ink stamped into metal: a faint highlight below + ink on top, optional tilt."""

    def __init__(
        self,
        text: str,
        font: QFont,
        ink_color: str,
        rotate_deg: float = 0.0,
        highlight_color: str = "rgba(255,215,180,0.35)",
        parent: QWidget | None = None,
    ):
        super().__init__(text, font, parent)
        self._ink = QColor(ink_color)
        self._rotate = rotate_deg
        self._highlight = self._parse(highlight_color)

    @staticmethod
    def _parse(color: str) -> QColor:
        if color.startswith("rgba"):
            parts = color[color.index("(") + 1 : color.index(")")].split(",")
            r, g, b = (int(p) for p in parts[:3])
            a = int(float(parts[3]) * 255)
            return QColor(r, g, b, a)
        return QColor(color)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(self.font())
        if self._rotate:
            center = self.rect().center()
            painter.translate(center)
            painter.rotate(self._rotate)
            painter.translate(-center)
        rect = self.rect()
        painter.setPen(self._highlight)
        painter.drawText(rect.translated(0, 1), Qt.AlignmentFlag.AlignCenter, self.text())
        painter.setPen(self._ink)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
        painter.end()
