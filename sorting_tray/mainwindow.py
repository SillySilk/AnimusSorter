"""Main window: assembles the three zones and owns project state + execute."""

from __future__ import annotations

import random
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .analysis import AnalyzeWorker, AutoSortWorker
from .analysis_ui import ConfirmCharactersDialog, SettingsDialog
from .assets import load_svg_pixmap
from .audio import SoundController
from .bins import BinPanel
from .controlbar import CategoryDialog, ControlBar
from .gallery import ID_ROLE, Gallery, GalleryFrame
from .llm import verify_server
from .painted import DebossedLabel
from .settings import Settings

log = get_logger("main")
from .loader import THUMB_BASE, ThumbnailLoader
from .models import (
    READABLE_EXTENSIONS,
    Category,
    ImageItem,
    Project,
    build_filename,
    export_as_png,
    next_serial_start,
)
from .styles import APP_QSS


def _placeholder_pixmap(size: int = THUMB_BASE) -> QPixmap:
    """QA reject tag for unreadable files: steel plate, ember hazard bands,
    tilted UNREADABLE stamp. Recognition only — the file stays binnable."""
    pm = QPixmap(size, size)
    pm.fill(QColor("#1a1a1a"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor("#232323"))
    grad.setColorAt(1.0, QColor("#1a1a1a"))
    p.fillRect(0, 0, size, size, QBrush(grad))

    band_h = size // 8
    stripe_w = size // 10
    p.setPen(Qt.PenStyle.NoPen)
    for band_top in (0, size - band_h):
        p.save()
        p.setClipRect(0, band_top, size, band_h)
        p.rotate(-45)
        p.setBrush(QColor("#a83a10"))
        for i in range(-3 * size // stripe_w, 3 * size // stripe_w):
            if i % 2 == 0:
                p.drawRect(QRectF(i * stripe_w, -2 * size, stripe_w, 5 * size))
        p.restore()

    p.save()
    p.translate(size / 2, size / 2)
    p.rotate(-8)
    font = QFont("DM Mono")
    font.setPixelSize(int(size * 0.11))
    font.setBold(True)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 110)
    p.setFont(font)
    fm = QFontMetrics(font)
    text = "UNREADABLE"
    pad = size * 0.035
    tw = fm.horizontalAdvance(text)
    rect = QRectF(-tw / 2 - pad, -fm.height() / 2 - pad, tw + 2 * pad, fm.height() + 2 * pad)
    p.setPen(QColor(0, 0, 0, 190))
    p.drawText(rect.translated(0, 2), Qt.AlignmentFlag.AlignCenter, text)
    p.setPen(QColor("#e2581f"))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    p.setPen(QPen(QColor(226, 88, 31, 200), max(2.0, size / 80)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(rect)
    p.restore()

    p.setPen(QPen(QColor("#0e0e0e"), 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(1, 1, size - 2, size - 2)
    p.end()
    return pm


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("sorting-tray")
        self.resize(1280, 820)
        self.setStyleSheet(APP_QSS)

        self.project: Project | None = None
        self.thumbs: dict[int, QPixmap] = {}
        self.tray_order: list[int] = []
        self.loader: ThumbnailLoader | None = None
        self.armed_bin: int | None = None
        self._anims: set = set()  # keep fly animations alive until they finish
        self._workers: set = set()  # keep analysis threads alive until they finish

        self.settings = Settings.load()
        self.sound = SoundController(self)

        self.control = ControlBar()
        self.gallery = Gallery()
        self.gallery_frame = GalleryFrame(self.gallery)
        self.bins = BinPanel()
        # The trays are large now, so they overflow vertically — house them in a
        # scroll area that grows a vertical scrollbar to reach the lower bins.
        self.bins_scroll = QScrollArea()
        self.bins_scroll.setObjectName("binsScroll")
        self.bins_scroll.setWidget(self.bins)
        self.bins_scroll.setWidgetResizable(True)
        self.bins_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.bins_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.bins_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.execute_btn = QPushButton("EXECUTE")
        self.execute_btn.setObjectName("executeButton")
        self.execute_btn.clicked.connect(self.on_execute)
        # Execute now rides in the control bar's left column, not a bottom bar.
        self.control.mount_execute(self.execute_btn)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.gallery_frame)
        split.addWidget(self.bins_scroll)
        # Give the bins roughly double their old share — they're now big square
        # trays — while the gallery stays the larger, dominant sorting tray.
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 3)
        split.setSizes([1150, 710])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.control)
        layout.addWidget(split, 1)
        layout.addWidget(self._build_footer())
        self.setCentralWidget(central)

        self.control.open_requested.connect(self.on_open)
        self.control.sort_changed.connect(self.on_sort)
        self.control.grid_size_changed.connect(self.gallery.set_icon_size)
        self.control.armed_changed.connect(self.on_armed_changed)
        self.control.sound_toggled.connect(self.sound.set_muted)
        self.gallery.tile_activated.connect(self.on_tile_activated)
        self.bins.images_dropped.connect(self.move_to_bin)
        self.bins.return_requested.connect(self.return_to_tray)
        self.bins.names_changed.connect(self.control.set_key_label)
        self.bins.analyze_requested.connect(self.on_analyze)
        self.bins.autosort_requested.connect(self.on_autosort)
        self.control.settings_requested.connect(self.on_settings)
        self.gallery.trash_requested.connect(self.trash_from_tray)

        self._set_enabled(False)
        self._update_execute_label()

    def _build_footer(self) -> QWidget:
        """Thin decorative maker's-plate strip: tool clip-art + forged-for mark."""
        bar = QWidget()
        bar.setObjectName("footerBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 4, 12, 4)
        row.setSpacing(8)
        rack = QLabel("THE RACK")
        rack.setObjectName("footerText")
        row.addWidget(rack)
        for name in ("anvil", "hammer", "flame", "horseshoe", "hexbolt"):
            icon = QLabel()
            icon.setPixmap(load_svg_pixmap(name, "#8a6a2f", 16))
            row.addWidget(icon)
        row.addStretch(1)
        plate = DebossedLabel("FORGED FOR ANIMA · MMXXVI", QLabel().font(), "#6f665a")
        plate.setObjectName("footerText")
        row.addWidget(plate)
        return bar

    def _update_execute_label(self) -> None:
        total = sum(len(bw.image_ids()) for bw in self.bins.bins)
        filled = sum(1 for bw in self.bins.bins if bw.image_ids())
        plural = "BIN" if filled == 1 else "BINS"
        self.execute_btn.setText(f"EXECUTE · {total} PRINTS · {filled} {plural}")

    def _update_gallery_status(self) -> None:
        if self.armed_bin is not None:
            self.gallery_frame.set_status(
                f"ARMED · BIN {self.armed_bin + 1} — CLICK PRINTS TO FILE", armed=True
            )
        else:
            n = len(self.tray_order)
            self.gallery_frame.set_status(f"{n} PRINTS UNSORTED", armed=False)

    def _set_enabled(self, on: bool) -> None:
        self.execute_btn.setEnabled(on)
        self.control.sort_box.setEnabled(on)
        self.control.grid_slider.setEnabled(on)
        for key in self.control.punch_keys:
            key.setEnabled(on)

    # --- open flow --------------------------------------------------------
    def on_open(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Open image folder")
        if not folder:
            return
        folder_path = Path(folder)

        dialog = CategoryDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted or dialog.choice is None:
            return
        category = dialog.choice

        paths = sorted(
            p for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() in READABLE_EXTENSIONS
        )
        if not paths:
            QMessageBox.information(self, "Empty", "No readable images in that folder.")
            return

        self.project = Project.open(folder_path, category)
        self.project.images = [ImageItem(path=p) for p in paths]
        self.thumbs.clear()
        self.tray_order = list(range(len(paths)))
        for bw in self.bins.bins:
            bw.clear_images()
            bw.set_flagged(False)
            bw.set_category_label(category.value)
        self.control.disarm()

        self.control.set_category(category)
        self.setWindowTitle(f"sorting-tray  —  {folder_path.name}  [{category.value}]")
        self._refresh_gallery()
        self._set_enabled(True)
        self._update_execute_label()
        self._update_gallery_status()
        log.info("opened %s [%s]: %d images, gallery shows %d",
                 folder_path.name, category.value, len(paths), self.gallery.count())
        self._start_loading()

    def _start_loading(self) -> None:
        assert self.project is not None
        self.loader = ThumbnailLoader(self)
        self.loader.thumb_ready.connect(self._on_thumb)
        items = [(i, img.path) for i, img in enumerate(self.project.images)]
        self.statusBar().showMessage(f"Loading {len(items)} thumbnails…")
        self.loader.finished.connect(lambda: self.statusBar().clearMessage())
        self.loader.load(items)

    def _on_thumb(self, image_id: int, qimg: QImage) -> None:
        pm = QPixmap.fromImage(qimg) if not qimg.isNull() else _placeholder_pixmap()
        self.thumbs[image_id] = pm
        item = self.project.images[image_id] if self.project else None
        if item is None:
            return
        if item.location == "tray":
            self.gallery.set_thumb(image_id, pm)
        elif isinstance(item.location, int):
            self.bins.bins[item.location].set_thumb(image_id, pm)

    # --- gallery / sorting ------------------------------------------------
    def _refresh_gallery(self) -> None:
        if not self.project:
            return
        ordered = [(i, self.project.images[i].path.name) for i in self.tray_order]
        self.gallery.repopulate(ordered)
        for i in self.tray_order:
            if i in self.thumbs:
                self.gallery.set_thumb(i, self.thumbs[i])

    def on_sort(self, mode: str) -> None:
        if not self.project:
            return
        imgs = self.project.images
        key = mode.lower()
        if key == "filename":
            self.tray_order.sort(key=lambda i: imgs[i].path.name.lower())
        elif key == "date modified":
            self.tray_order.sort(key=lambda i: imgs[i].path.stat().st_mtime)
        elif key == "file size":
            self.tray_order.sort(key=lambda i: imgs[i].path.stat().st_size)
        elif key == "random":
            random.shuffle(self.tray_order)
        self._refresh_gallery()

    # --- arming / click-to-shoot -----------------------------------------
    def on_armed_changed(self, idx: int) -> None:
        was_armed = self.armed_bin is not None
        self.armed_bin = idx if idx >= 0 else None
        log.debug("armed bin -> %s", self.armed_bin)
        # Mechanical key SFX: ka-chunk on any latch (including a switch), pop on
        # full release. Programmatic disarm with nothing armed stays silent.
        if self.armed_bin is not None:
            self.sound.play_push()
        elif was_armed:
            self.sound.play_release()
        self.gallery.set_armed_mode(self.armed_bin is not None)
        for bw in self.bins.bins:
            bw.set_armed(bw.index == self.armed_bin)
        self._update_gallery_status()

    def on_tile_activated(self, image_id: int) -> None:
        """While a bin is latched, each clicked thumbnail flies straight to it."""
        log.debug("tile activated: id=%s armed_bin=%s", image_id, self.armed_bin)
        if self.armed_bin is None or not self.project:
            return
        self._fly_to_bin(image_id, self.armed_bin)

    def _fly_to_bin(self, image_id: int, bin_index: int) -> None:
        """Move the image, then animate a copy of its thumbnail into the bin."""
        gallery_item = self.gallery._items.get(image_id)
        pixmap = self.thumbs.get(image_id)
        start: QRect | None = None
        if gallery_item is not None:
            vr = self.gallery.visualItemRect(gallery_item)
            top_left = self.gallery.viewport().mapToGlobal(vr.topLeft())
            start = QRect(self.centralWidget().mapFromGlobal(top_left), vr.size())

        self.move_to_bin(bin_index, [image_id])

        if start is None or pixmap is None or pixmap.isNull():
            return

        bw = self.bins.bins[bin_index]
        center_global = bw.mapToGlobal(bw.rect().center())
        center = self.centralWidget().mapFromGlobal(center_global)
        end_side = max(24, start.width() // 5)  # shrink to bin-thumbnail size
        end = QRect(center.x() - end_side // 2, center.y() - end_side // 2, end_side, end_side)

        flyer = QLabel(self.centralWidget())
        flyer.setScaledContents(True)
        flyer.setPixmap(pixmap)
        flyer.setGeometry(start)
        flyer.show()
        flyer.raise_()

        anim = QPropertyAnimation(flyer, b"geometry", self)
        anim.setDuration(260)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.finished.connect(flyer.deleteLater)
        anim.finished.connect(lambda: self._anims.discard(anim))
        self._anims.add(anim)
        anim.start()

    # --- moves ------------------------------------------------------------

    def move_to_bin(self, bin_index: int, ids: list[int]) -> None:
        log.debug("move_to_bin: bin=%s ids=%s", bin_index, ids)
        if not self.project:
            log.warning("move_to_bin ignored: no project open")
            return
        bw = self.bins.bins[bin_index]
        for image_id in ids:
            item = self.project.images[image_id]
            if item.location == bin_index:
                continue
            # Pull out of wherever it currently sits.
            if item.location == "tray" and image_id in self.tray_order:
                self.tray_order.remove(image_id)
            elif isinstance(item.location, int):
                self.bins.bins[item.location].remove_ids([image_id])
            item.location = bin_index
            bw.add_image(image_id, self.thumbs.get(image_id), item.path.name)
        self.gallery.remove_ids(ids)
        self._update_execute_label()
        self._update_gallery_status()

    def return_to_tray(self, bin_index: int, ids: list[int]) -> None:
        if not self.project:
            return
        self.bins.bins[bin_index].remove_ids(ids)
        for image_id in ids:
            item = self.project.images[image_id]
            item.location = "tray"
            if image_id not in self.tray_order:
                self.tray_order.append(image_id)
        self._refresh_gallery()
        self._update_execute_label()
        self._update_gallery_status()

    def trash_from_tray(self, ids: list[int]) -> None:
        """Optionally delete unsorted tray junk from disk, with confirm."""
        if not self.project or not ids:
            return
        resp = QMessageBox.question(
            self, "Delete from disk",
            f"Permanently delete {len(ids)} image(s) from the folder?\n"
            "This removes the files on disk and cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for image_id in ids:
            item = self.project.images[image_id]
            if item.location != "tray":
                continue
            try:
                item.path.unlink()
            except OSError as exc:
                errors.append(f"{item.path.name}: {exc.strerror or exc}")
                continue
            if image_id in self.tray_order:
                self.tray_order.remove(image_id)
        self.gallery.remove_ids(ids)
        self._update_gallery_status()
        if errors:
            QMessageBox.warning(self, "Some files not deleted", "\n".join(errors[:12]))

    # --- AI assist: analyze + auto-sort -----------------------------------
    def on_settings(self) -> None:
        SettingsDialog(self.settings, self).exec()

    def _llm_config(self):
        return self.settings.get("lmstudio_url"), self.settings.get("lmstudio_model")

    def _server_ready(self) -> bool:
        url, _model = self._llm_config()
        ok, detail = verify_server(url)
        if not ok:
            QMessageBox.warning(
                self, "LM Studio not ready",
                f"{detail}\n\nStart LM Studio, load a vision model, then try again.\n"
                f"(Configure the URL/model with the ⚙ button.)",
            )
        return ok

    def on_analyze(self, bin_index: int) -> None:
        if not self.project or not self._server_ready():
            return
        bw = self.bins.bins[bin_index]
        ids = bw.image_ids()
        paths = [str(self.project.images[i].path) for i in ids]
        names = [n.strip() for n in bw.names() if n.strip()]
        url, model = self._llm_config()
        bw.set_busy(True)
        self.statusBar().showMessage(f"Analyzing {len(paths)} images in bin {bin_index + 1}…")
        worker = AnalyzeWorker(paths, names, self.project.category.value, url, model, self)
        worker.finished_ok.connect(lambda figs, b=bin_index, oids=ids: self._analyze_done(b, oids, figs))
        worker.failed.connect(lambda msg, b=bin_index: self._analyze_failed(b, msg))
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        self._workers.add(worker)
        worker.start()

    def _analyze_failed(self, bin_index: int, msg: str) -> None:
        self.bins.bins[bin_index].set_busy(False)
        self.statusBar().clearMessage()
        QMessageBox.warning(self, "Analyze failed", msg)

    def _analyze_done(self, bin_index: int, ids: list[int], figures: list) -> None:
        bw = self.bins.bins[bin_index]
        self.statusBar().clearMessage()
        figures_with_thumbs = []
        for fig in figures:
            rep = fig.get("rep_index", 0)
            image_id = ids[rep] if 0 <= rep < len(ids) else (ids[0] if ids else None)
            pm = self.thumbs.get(image_id) if image_id is not None else None
            figures_with_thumbs.append((fig.get("description", ""), pm))
        names = [n.strip() for n in bw.names() if n.strip()]
        dialog = ConfirmCharactersDialog(figures_with_thumbs, names, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            bw.set_roster(dialog.result_roster())
            self.statusBar().showMessage(
                f"Bin {bin_index + 1} ready to auto-sort — {len(bw.roster)} subject(s) profiled.",
                6000)
        bw.set_busy(False)

    def on_autosort(self, bin_index: int) -> None:
        if not self.project or not self._server_ready():
            return
        bw = self.bins.bins[bin_index]
        items = [(i, str(self.project.images[i].path)) for i in self.tray_order]
        if not items:
            QMessageBox.information(self, "Tray empty", "No unsorted images left to scan.")
            return
        resp = QMessageBox.question(
            self, "Auto-sort tray",
            f"Scan {len(items)} tray image(s) and file the ones that match "
            f"“{' · '.join(bw.roster)}”?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        names = [n.strip() for n in bw.names() if n.strip()]
        url, model = self._llm_config()
        bw.set_busy(True)

        progress = QProgressDialog(
            f"Scanning tray for bin {bin_index + 1}…", "Cancel", 0, len(items), self)
        progress.setWindowTitle("Auto-sort")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        worker = AutoSortWorker(items, bw.roster, names, self.project.category.value, url, model, self)
        worker.progress.connect(
            lambda scanned, total, filed: self._autosort_progress(progress, scanned, total, filed))
        worker.matched.connect(lambda image_id, b=bin_index: self.move_to_bin(b, [image_id]))
        worker.finished_ok.connect(
            lambda filed, scanned, b=bin_index: self._autosort_done(b, progress, filed, scanned))
        worker.failed.connect(lambda msg, b=bin_index: self._autosort_failed(b, progress, msg))
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        progress.canceled.connect(worker.cancel)
        self._workers.add(worker)
        worker.start()

    def _autosort_progress(self, progress, scanned, total, filed) -> None:
        progress.setLabelText(f"Scanned {scanned}/{total} · {filed} filed")
        progress.setValue(scanned)

    def _autosort_done(self, bin_index, progress, filed, scanned) -> None:
        progress.close()
        self.bins.bins[bin_index].set_busy(False)
        QMessageBox.information(
            self, "Auto-sort done",
            f"Filed {filed} of {scanned} scanned image(s) into bin {bin_index + 1}.\n"
            f"Unmatched images stayed in the tray.")

    def _autosort_failed(self, bin_index, progress, msg) -> None:
        progress.close()
        self.bins.bins[bin_index].set_busy(False)
        QMessageBox.warning(self, "Auto-sort failed", msg)

    # --- execute ----------------------------------------------------------
    def on_execute(self) -> None:
        if not self.project:
            return
        category = self.project.category
        folder = self.project.folder_path

        # Validation: every non-empty bin needs all its name boxes filled.
        offenders: list[int] = []
        active: list[tuple] = []  # (bin_widget, ids, name_block)
        for bw in self.bins.bins:
            ids = bw.image_ids()
            if not ids:
                bw.set_flagged(False)
                continue
            names = [n.strip() for n in bw.names()]
            if not all(names):
                bw.set_flagged(True)
                offenders.append(bw.index + 1)
            else:
                bw.set_flagged(False)
                active.append((bw, ids, "-".join(names)))

        if offenders:
            QMessageBox.warning(
                self, "Missing names",
                "These bins hold images but have empty name boxes:\n\n"
                f"Bin {', Bin '.join(str(n) for n in offenders)}\n\n"
                "Fill every name box or empty the bin, then execute again.",
            )
            return

        if not active:
            QMessageBox.information(self, "Nothing to do", "No bins hold images.")
            return

        # Non-blocking hyphen warning (a hyphen inside one name reads as two subjects).
        hyphenated = sorted({
            n for bw, _ids, _nb in active for n in (s.strip() for s in bw.names()) if "-" in n
        })
        if hyphenated:
            resp = QMessageBox.question(
                self, "Hyphen in a name",
                "A hyphen separates subjects, so these names will be read as "
                "multiple subjects:\n\n"
                + "\n".join(f"  • {n}" for n in hyphenated)
                + "\n\nContinue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return

        renamed, errors = self._rename(active, folder, category)
        self._update_execute_label()
        self._update_gallery_status()

        summary = (
            f"Sorted {renamed} image(s) from {len(active)} bin(s) into the "
            f"'sorted' subfolder.\n\nThe bins are now empty — keep sorting what's "
            f"left in the tray and process again when ready."
        )
        if errors:
            summary += "\n\nErrors:\n" + "\n".join(errors[:12])
            if len(errors) > 12:
                summary += f"\n…and {len(errors) - 12} more."
            QMessageBox.warning(self, "Done with errors", summary)
        else:
            QMessageBox.information(self, "Done", summary)

    def _rename(self, active, folder: Path, category: Category):
        renamed = 0
        errors: list[str] = []
        # Sorted images leave the working folder for a `sorted/` subfolder, like
        # bagging up a finished bin and putting it away — what's left in the tray
        # is all that still needs sorting. Every export is written as PNG; the
        # original file (any format) is consumed by the conversion.
        dest = folder / "sorted"
        dest.mkdir(exist_ok=True)
        total = sum(len(ids) for _bw, ids, _nb in active)
        progress = QProgressDialog("Exporting to PNG…", None, 0, total, self)
        progress.setWindowTitle("Executing")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        done = 0
        for bw, ids, name_block in active:
            serial = next_serial_start(dest, name_block, category.value)
            for image_id in ids:
                item = self.project.images[image_id]
                # Skip past any name that is already taken in the sorted folder.
                while True:
                    target = dest / build_filename(name_block, serial, category.value, ".png")
                    if not target.exists() or target == item.path:
                        break
                    serial += 1
                try:
                    if target != item.path:
                        export_as_png(item.path, target)
                        item.path = target
                    renamed += 1
                    serial += 1
                except Exception as exc:
                    errors.append(f"{item.path.name}: {exc}")
                done += 1
                progress.setValue(done)
                progress.setLabelText(f"Exporting to PNG… {done}/{total}")
            bw.clear_images()
        progress.close()
        return renamed, errors
