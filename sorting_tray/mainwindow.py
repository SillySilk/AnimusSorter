"""Main window: assembles the three zones and owns project state + execute."""

from __future__ import annotations

import random
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .applog import get_logger
from .bins import BinPanel
from .controlbar import CategoryDialog, ControlBar
from .gallery import ID_ROLE, Gallery

log = get_logger("main")
from .loader import ThumbnailLoader
from .models import (
    READABLE_EXTENSIONS,
    Category,
    ImageItem,
    Project,
    build_filename,
    next_serial_start,
)
from .styles import APP_QSS


def _placeholder_pixmap(size: int = 96) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(QColor("#3a3a3a"))
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

        self.control = ControlBar()
        self.gallery = Gallery()
        self.bins = BinPanel()
        self.execute_btn = QPushButton("START PROCESSING")
        self.execute_btn.setObjectName("executeButton")
        self.execute_btn.clicked.connect(self.on_execute)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.gallery)
        split.addWidget(self.bins)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([760, 500])

        # Top row: control bar fills the width, Start Processing pinned top-right.
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 8, 0)
        top_row.setSpacing(8)
        top_row.addWidget(self.control, 1)
        top_row.addWidget(self.execute_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(top_row)
        layout.addWidget(split, 1)
        self.setCentralWidget(central)

        self.control.open_requested.connect(self.on_open)
        self.control.sort_changed.connect(self.on_sort)
        self.control.grid_size_changed.connect(self.gallery.set_icon_size)
        self.control.armed_changed.connect(self.on_armed_changed)
        self.gallery.tile_activated.connect(self.on_tile_activated)
        self.bins.images_dropped.connect(self.move_to_bin)
        self.bins.return_requested.connect(self.return_to_tray)
        self.gallery.trash_requested.connect(self.trash_from_tray)

        self._set_enabled(False)

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
        self.control.disarm()

        self.control.set_category(category)
        self.setWindowTitle(f"sorting-tray  —  {folder_path.name}  [{category.value}]")
        self._refresh_gallery()
        self._set_enabled(True)
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
        self.armed_bin = idx if idx >= 0 else None
        log.debug("armed bin -> %s", self.armed_bin)
        self.gallery.set_armed_mode(self.armed_bin is not None)
        for bw in self.bins.bins:
            bw.set_armed(bw.index == self.armed_bin)

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
        if errors:
            QMessageBox.warning(self, "Some files not deleted", "\n".join(errors[:12]))

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
        # is all that still needs sorting.
        dest = folder / "sorted"
        dest.mkdir(exist_ok=True)
        for bw, ids, name_block in active:
            serial = next_serial_start(dest, name_block, category.value)
            for image_id in ids:
                item = self.project.images[image_id]
                ext = item.path.suffix
                # Skip past any name that is already taken in the sorted folder.
                while True:
                    target = dest / build_filename(name_block, serial, category.value, ext)
                    if not target.exists() or target == item.path:
                        break
                    serial += 1
                try:
                    if target != item.path:
                        item.path.rename(target)
                        item.path = target
                    renamed += 1
                    serial += 1
                except OSError as exc:
                    errors.append(f"{item.path.name}: {exc.strerror or exc}")
            bw.clear_images()
        return renamed, errors
