"""Batch queue data and drop-aware list widget."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QAbstractItemView, QListWidget

from .imaging import IMAGE_EXTENSIONS


@dataclass
class BatchItem:
    id: int
    path: Path
    settings: dict
    work_dir: Path
    status: str = "queued"      # queued, running, ready, editing, edited, error
    masks_path: Path | None = None
    state_path: Path | None = None
    n_cells: int = 0
    counted: int = 0
    error: str = ""


class BatchListWidget(QListWidget):
    filesDropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setTextElideMode(Qt.ElideMiddle)
        self.setAlternatingRowColors(True)
        self.setMinimumHeight(110)
        self.setToolTip("把多张图像拖到这里，自动排队处理")

    def _image_paths(self, mime) -> list[str]:
        out = []
        if not mime.hasUrls():
            return out
        for url in mime.urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                out.append(str(p))
        return out

    def dragEnterEvent(self, event):
        if self._image_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._image_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = self._image_paths(event.mimeData())
        if files:
            self.filesDropped.emit(files)
            event.acceptProposedAction()
        else:
            event.ignore()
