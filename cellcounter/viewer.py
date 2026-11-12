"""Interactive image viewer with mask overlay, drawing and counting tools."""

from __future__ import annotations

import math
from typing import Iterable

import cv2
import numpy as np
from PyQt5.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (
    QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPolygonF,
)
from PyQt5.QtWidgets import QWidget

from . import i18n, theme
from .model import CellStore
from .overlay_style import OverlayStyle


class ImageViewer(QWidget):
    positionChanged = pyqtSignal(str)
    zoomChanged = pyqtSignal(float)
    editApplied = pyqtSignal(str)
    selectionChanged = pyqtSignal(list)
    modeRequested = pyqtSignal(int)
    calibrationFinished = pyqtSignal(float, float, float, float)
    calibrationCancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMinimumSize(360, 260)

        self.store: CellStore | None = None
        self.image_rgb: np.ndarray | None = None
        self._qimage: QImage | None = None
        self._overlay: QImage | None = None
        self._overlay_dirty = True

        self.scale = 1.0
        self.ox = 0.0
        self.oy = 0.0
        self._auto_fit = True

        self.mode = 1
        self.show_labels = True
        self.overlay_opacity = 1.0
        self.fill_cells = False
        self.style = OverlayStyle()
        self.selected: set[int] = set()
        self.preview_ids: set[int] = set()
        self.hover_id: int | None = None
        self.calibration_mode = False
        self.calibration_points: list[tuple[float, float]] = []
        self.calibration_label = ""
        self._calib_cursor: tuple[float, float] | None = None

        self._space_down = False
        self._drag: str | None = None
        self._press_screen = QPoint()
        self._last_screen = QPoint()
        self._moved = False
        self._draw_points: list[tuple[float, float]] = []
        self._box_rect: QRectF | None = None
        self._box_kind = ""

    # ------------------------------------------------------------- data setup
    def set_image(self, rgb: np.ndarray | None, keep_view: bool = False):
        self.image_rgb = rgb
        if rgb is None:
            self._qimage = None
        else:
            h, w = rgb.shape[:2]
            rgb = np.ascontiguousarray(rgb)
            self._qimage = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        if not keep_view:
            self._auto_fit = True
            self.selected.clear()
            self.preview_ids.clear()
            self.hover_id = None
            self._drag = None
            self.calibration_mode = False
            self.calibration_points = []
            self.calibration_label = ""
            self._calib_cursor = None
        self._overlay_dirty = True
        self.update()

    def _draw_calibration(self, p: QPainter):
        pts = self.calibration_points
        if not pts:
            return
        color = QColor(theme.ORANGE)
        pen = QPen(color, 2.2, Qt.DashLine if self.calibration_mode else Qt.SolidLine)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        screen = [self.image_to_screen(x, y) for x, y in pts]
        if len(pts) == 1 and self.calibration_mode and self._calib_cursor:
            cx, cy = self.image_to_screen(*self._calib_cursor)
            p.drawLine(QPointF(*screen[0]), QPointF(cx, cy))
        if len(pts) >= 2:
            p.drawLine(QPointF(*screen[0]), QPointF(*screen[1]))
        for sx, sy in screen:
            p.setBrush(QBrush(color))
            p.setPen(QPen(QColor(10, 16, 28), 1))
            p.drawEllipse(QPointF(sx, sy), 4, 4)
        if len(pts) >= 2:
            if self.calibration_label:
                text = self.calibration_label
            else:
                length = math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
                text = f"{length:.1f} px"
            mx = (screen[0][0] + screen[1][0]) / 2.0
            my = (screen[0][1] + screen[1][1]) / 2.0 - 18
            p.setFont(QFont(theme.MONO_FAMILY, 8))
            fm = p.fontMetrics()
            w = fm.horizontalAdvance(text) + 12
            h = fm.height() + 6
            rect = QRectF(mx - w / 2, my - h / 2, w, h)
            p.setBrush(QBrush(QColor(6, 12, 24, 210)))
            p.setPen(QPen(color, 1))
            p.drawRoundedRect(rect, 4, 4)
            p.setPen(QColor(255, 255, 255))
            p.drawText(rect, Qt.AlignCenter, text)

    def set_store(self, store: CellStore | None):
        self.store = store
        self._overlay_dirty = True
        self.selected.clear()
        self.preview_ids.clear()
        self.hover_id = None
        self.update()

    def refresh(self):
        self._overlay_dirty = True
        if self.store is not None:
            self.selected &= set(self.store.metas)
            self.preview_ids &= set(self.store.metas)
        self.update()

    def set_mode(self, mode: int):
        self.mode = 2 if mode == 2 else 1
        self._drag = None
        self._box_rect = None
        self._draw_points.clear()
        self.preview_ids.clear()
        self.clear_calibration_line()
        self._update_cursor(Qt.NoModifier)
        self.update()

    def start_calibration(self):
        self.calibration_mode = True
        self.calibration_points = []
        self.calibration_label = ""
        self._calib_cursor = None
        self._drag = None
        self.setCursor(Qt.CrossCursor)
        self.update()

    def cancel_calibration(self):
        active = self.calibration_mode or bool(self.calibration_points)
        self.calibration_mode = False
        self.calibration_points = []
        self.calibration_label = ""
        self._calib_cursor = None
        self._update_cursor(Qt.NoModifier)
        self.update()
        if active:
            self.calibrationCancelled.emit()

    def clear_calibration_line(self):
        had = bool(self.calibration_points)
        self.calibration_mode = False
        self.calibration_points = []
        self.calibration_label = ""
        self._calib_cursor = None
        self._update_cursor(Qt.NoModifier)
        self.update()
        return had

    def set_calibration_line(self, p1, p2, label: str = ""):
        self.calibration_mode = False
        self.calibration_points = [(float(p1[0]), float(p1[1])),
                                   (float(p2[0]), float(p2[1]))]
        self.calibration_label = label
        self._calib_cursor = None
        self._update_cursor(Qt.NoModifier)
        self.update()

    def set_preview(self, ids: Iterable[int]):
        if self.store is None:
            self.preview_ids = set()
        else:
            self.preview_ids = {int(i) for i in ids if int(i) in self.store.metas}
        self._overlay_dirty = True
        self.update()

    def clear_preview(self):
        if not self.preview_ids:
            return
        self.preview_ids.clear()
        self._overlay_dirty = True
        self.update()

    def set_show_labels(self, on: bool):
        self.show_labels = bool(on)
        self.update()

    def set_overlay_opacity(self, value: float):
        self.overlay_opacity = max(0.0, min(1.0, float(value)))
        self.update()

    def set_fill_cells(self, on: bool):
        self.fill_cells = bool(on)
        self._overlay_dirty = True
        self.update()

    def set_style(self, style: OverlayStyle):
        self.style = style.copy()
        self._overlay_dirty = True
        self.update()

    # ---------------------------------------------------------------- geometry
    def _image_size(self):
        if self.image_rgb is None:
            return 0, 0
        h, w = self.image_rgb.shape[:2]
        return w, h

    def fit(self):
        w, h = self._image_size()
        if w == 0 or h == 0:
            return
        vw, vh = self.width(), self.height()
        self.scale = max(0.005, min((vw - 36) / w, (vh - 36) / h))
        self.ox = (vw - w * self.scale) / 2.0
        self.oy = (vh - h * self.scale) / 2.0
        self._auto_fit = True
        self.zoomChanged.emit(self.scale)
        self.update()

    def reset_100(self):
        if self.image_rgb is None:
            return
        w, h = self._image_size()
        self.scale = 1.0
        self.ox = (self.width() - w) / 2.0
        self.oy = (self.height() - h) / 2.0
        self._auto_fit = False
        self.zoomChanged.emit(self.scale)
        self.update()

    def screen_to_image(self, pos: QPoint | QPointF):
        x = (pos.x() - self.ox) / self.scale
        y = (pos.y() - self.oy) / self.scale
        return x, y

    def image_to_screen(self, x: float, y: float):
        return self.ox + x * self.scale, self.oy + y * self.scale

    def _inside(self, x: float, y: float) -> bool:
        w, h = self._image_size()
        return 0 <= x < w and 0 <= y < h

    def _hit_test(self, pos: QPoint) -> int | None:
        if self.store is None:
            return None
        x, y = self.screen_to_image(pos)
        if not self._inside(x, y):
            return None
        yy, xx = int(y), int(x)
        if yy < 0 or xx < 0 or yy >= self.store.labels.shape[0] or xx >= self.store.labels.shape[1]:
            return None
        cid = int(self.store.labels[yy, xx])
        return cid if cid > 0 else None

    def _ids_in_screen_rect(self, rect: QRectF) -> list[int]:
        if self.store is None:
            return []
        x0, y0 = self.screen_to_image(rect.topLeft())
        x1, y1 = self.screen_to_image(rect.bottomRight())
        x0, x1 = sorted((x0, x1))
        y0, y1 = sorted((y0, y1))
        out = []
        for cid in self.store.metas:
            st = self.store.stats.get(cid)
            if st is None:
                continue
            if x0 <= st.cx <= x1 and y0 <= st.cy <= y1:
                out.append(cid)
        return out

    def zoom_to_cell(self, cid: int):
        if self.store is None:
            return
        st = self.store.stats.get(cid)
        if st is None:
            return
        w, h = self._image_size()
        target = max(self.scale, min(4.0, max(1.2, 120.0 / max(1.0, math.sqrt(st.area)))))
        target = max(0.02, min(40.0, target))
        self.scale = target
        self.ox = self.width() / 2.0 - st.cx * self.scale
        self.oy = self.height() / 2.0 - st.cy * self.scale
        self._auto_fit = False
        self.zoomChanged.emit(self.scale)
        self.set_selection([cid])
        self.update()

    # ------------------------------------------------------------------ events
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._auto_fit:
            self.fit()

    def wheelEvent(self, event):
        if self.image_rgb is None:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.18 if delta > 0 else 1 / 1.18
        old = self.scale
        new = max(0.01, min(60.0, old * factor))
        if new == old:
            return
        pos = event.pos()
        ix, iy = self.screen_to_image(pos)
        self.scale = new
        self.ox = pos.x() - ix * new
        self.oy = pos.y() - iy * new
        self._auto_fit = False
        self.zoomChanged.emit(self.scale)
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        self.setFocus()
        if self.image_rgb is None:
            return
        self._press_screen = event.pos()
        self._last_screen = event.pos()
        self._moved = False
        self._draw_points.clear()
        self._box_rect = None
        self._box_bounds = None
        self._box_kind = ""

        if event.button() in (Qt.MiddleButton, Qt.RightButton) or (
                event.button() == Qt.LeftButton and self._space_down):
            self._drag = "pan"
            self._update_cursor(event.modifiers())
            return
        if event.button() != Qt.LeftButton:
            return

        if self.calibration_mode:
            x, y = self.screen_to_image(event.pos())
            if self._inside(x, y):
                self.calibration_points.append((x, y))
                if len(self.calibration_points) >= 2:
                    p1, p2 = self.calibration_points[-2:]
                    self.calibration_mode = False
                    self._calib_cursor = None
                    self._update_cursor(event.modifiers())
                    self.update()
                    self.calibrationFinished.emit(p1[0], p1[1], p2[0], p2[1])
                else:
                    self.update()
            return

        alt = bool(event.modifiers() & Qt.AltModifier)
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)

        if self.mode == 1:
            if alt:
                self._drag = "box_delete"
            elif ctrl:
                self._drag = "click_toggle"
            else:
                self._drag = "draw"
                self._draw_points = [self.screen_to_image(event.pos())]
        else:
            if alt:
                self._drag = "box_delete"
            elif shift:
                self._drag = "draw"
                self._draw_points = [self.screen_to_image(event.pos())]
            elif ctrl:
                self._drag = "box_uncount"
            else:
                self._drag = "box_count"
        if self._drag.startswith("box"):
            self._box_bounds = [
                float(event.pos().x()), float(event.pos().y()),
                float(event.pos().x()), float(event.pos().y()),
            ]
        self._update_cursor(event.modifiers())
        self.update()

    def mouseMoveEvent(self, event):
        if self.image_rgb is None:
            return
        pos = event.pos()
        if self._drag == "pan":
            dx = pos.x() - self._last_screen.x()
            dy = pos.y() - self._last_screen.y()
            self.ox += dx
            self.oy += dy
            self._last_screen = pos
            self._auto_fit = False
            self.update()
            return

        if (pos - self._press_screen).manhattanLength() > 3:
            self._moved = True

        if self.calibration_mode:
            x, y = self.screen_to_image(pos)
            self._calib_cursor = (x, y) if self._inside(x, y) else None
            self.update()

        if self._drag == "draw":
            x, y = self.screen_to_image(pos)
            if not self._draw_points or (
                    abs(x - self._draw_points[-1][0]) > 0.6 or
                    abs(y - self._draw_points[-1][1]) > 0.6):
                self._draw_points.append((x, y))
            self.update()
        elif self._drag and self._drag.startswith("box"):
            if self._box_bounds is None:
                self._box_bounds = [
                    float(self._press_screen.x()), float(self._press_screen.y()),
                    float(pos.x()), float(pos.y()),
                ]
            b = self._box_bounds
            b[0] = min(b[0], float(pos.x()))
            b[1] = min(b[1], float(pos.y()))
            b[2] = max(b[2], float(pos.x()))
            b[3] = max(b[3], float(pos.y()))
            self._box_rect = QRectF(b[0], b[1], b[2] - b[0], b[3] - b[1])
            if self._drag == "box_delete":
                self._box_kind = "delete"
            elif self._drag == "box_uncount":
                self._box_kind = "uncount"
            else:
                self._box_kind = "count"
            self.update()

        x, y = self.screen_to_image(pos)
        cid = self._hit_test(pos)
        if cid != self.hover_id:
            self.hover_id = cid
            self.update()
        if self._inside(x, y):
            text = f"x {x:.1f}  y {y:.1f}"
            if cid is not None and self.store is not None:
                st = self.store.stats.get(cid)
                src = "手动" if self.store.metas[cid].origin == "manual" else "自动"
                state = "已计数" if self.store.metas[cid].counted else "未计数"
                if st:
                    text += f"   ·   细胞 {cid} · {state} · {src} · {st.area} px²"
            self.positionChanged.emit(text)
        else:
            self.positionChanged.emit("")
        self._last_screen = pos
        self._update_cursor(event.modifiers())

    def mouseReleaseEvent(self, event):
        if self._drag is None:
            return
        drag = self._drag
        self._drag = None
        pos = event.pos()

        if drag == "pan":
            self._update_cursor(event.modifiers())
            self.update()
            return

        if drag == "draw":
            if self._moved and len(self._draw_points) >= 3:
                pts = np.asarray(self._draw_points, np.float64)
                if cv2.contourArea(pts.astype(np.float32)) >= 6:
                    cid = self.store.add_polygon(pts, counted=True) if self.store else None
                    self._draw_points.clear()
                    self._finish_edit("已添加手动标注" if cid else "绘制区域太小")
                else:
                    self._draw_points.clear()
                    self._finish_edit("绘制区域太小")
                return
            self._draw_points.clear()
            if self.mode == 1 and not (event.modifiers() & Qt.AltModifier):
                cid = self._hit_test(pos)
                self.set_selection([cid] if cid else [])
            self.update()
            return

        if drag == "click_toggle":
            cid = self._hit_test(pos)
            if cid is not None and self.store is not None:
                n = self.store.toggle_counted(cid)
                if n:
                    self._finish_edit("已切换计数状态")
            self._update_cursor(event.modifiers())
            self.update()
            return

        if drag.startswith("box"):
            if not self._moved:
                cid = self._hit_test(pos)
                if cid is None or self.store is None:
                    self._box_rect = None
                    self.update()
                    return
                if drag == "box_delete":
                    n = self.store.delete_cells([cid])
                    self._finish_edit(f"已删除细胞 {cid}" if n else "")
                elif drag == "box_uncount":
                    n = self.store.set_counted([cid], False)
                    self._finish_edit("已取消计数" if n else "")
                else:
                    n = self.store.toggle_counted(cid)
                    self._finish_edit("已切换计数状态" if n else "")
            else:
                if self._box_bounds is not None:
                    b = self._box_bounds
                    rect = QRectF(b[0], b[1], b[2] - b[0], b[3] - b[1])
                else:
                    rect = QRectF(QPointF(self._press_screen), QPointF(pos)).normalized()
                ids = self._ids_in_screen_rect(rect)
                if not ids:
                    self._finish_edit("框选范围内没有细胞")
                elif drag == "box_delete":
                    n = self.store.delete_cells(ids)
                    self._finish_edit(f"已删除 {n} 个细胞")
                elif drag == "box_uncount":
                    n = self.store.set_counted(ids, False)
                    self._finish_edit(f"已取消 {n} 个细胞的计数")
                else:
                    n = self.store.set_counted(ids, True)
                    self._finish_edit(f"已计数 {n} 个细胞")
            self._box_rect = None
            self._box_bounds = None
            self._box_kind = ""
            self.update()
            return

    def leaveEvent(self, event):
        self.hover_id = None
        self.positionChanged.emit("")
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Space and not event.isAutoRepeat():
            self._space_down = True
            self._update_cursor(event.modifiers())
            event.accept()
            return
        if key == Qt.Key_Escape:
            if self.calibration_mode or self.calibration_points:
                self.cancel_calibration()
                event.accept()
                return
            self._drag = None
            self._draw_points.clear()
            self._box_rect = None
            self.set_selection([])
            self.update()
            event.accept()
            return
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected and self.store is not None:
                n = self.store.delete_cells(self.selected)
                self.selected.clear()
                self.selectionChanged.emit([])
                self._finish_edit(f"已删除 {n} 个细胞")
            event.accept()
            return
        if key == Qt.Key_F:
            self.fit()
            event.accept()
            return
        if key in (Qt.Key_Plus, Qt.Key_Equal):
            self._zoom_center(1.25)
            event.accept()
            return
        if key == Qt.Key_Minus:
            self._zoom_center(1 / 1.25)
            event.accept()
            return
        if key == Qt.Key_1:
            self.modeRequested.emit(1)
            event.accept()
            return
        if key == Qt.Key_2:
            self.modeRequested.emit(2)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._space_down = False
            self._update_cursor(event.modifiers())
            event.accept()
            return
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self._space_down = False
        super().focusOutEvent(event)

    def _zoom_center(self, factor: float):
        if self.image_rgb is None:
            return
        pos = QPointF(self.width() / 2.0, self.height() / 2.0)
        ix, iy = self.screen_to_image(pos)
        new = max(0.01, min(60.0, self.scale * factor))
        if new == self.scale:
            return
        self.scale = new
        self.ox = pos.x() - ix * new
        self.oy = pos.y() - iy * new
        self._auto_fit = False
        self.zoomChanged.emit(self.scale)
        self.update()

    # ---------------------------------------------------------------- selection
    def set_selection(self, ids: Iterable[int]):
        if self.store is None:
            self.selected = set()
        else:
            self.selected = {int(i) for i in ids if int(i) in self.store.metas}
        self.selectionChanged.emit(sorted(self.selected))
        self.update()

    def _finish_edit(self, message: str):
        self._overlay_dirty = True
        if self.store is not None:
            self.selected &= set(self.store.metas)
        self._box_rect = None
        self._box_kind = ""
        self.editApplied.emit(message)
        self.update()

    # ------------------------------------------------------------------ cursor
    def _update_cursor(self, modifiers):
        if self._drag == "pan":
            self.setCursor(Qt.ClosedHandCursor)
            return
        if self.calibration_mode:
            self.setCursor(Qt.CrossCursor)
            return
        if self._space_down:
            self.setCursor(Qt.OpenHandCursor)
            return
        if modifiers & Qt.AltModifier:
            self.setCursor(Qt.ForbiddenCursor)
            return
        draw_mode = (self.mode == 1 and not (modifiers & Qt.ControlModifier)) or (
            self.mode == 2 and (modifiers & Qt.ShiftModifier))
        if draw_mode:
            self.setCursor(Qt.CrossCursor)
        elif self.hover_id is not None:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    # ----------------------------------------------------------------- painting
    def _ensure_overlay(self):
        if not self._overlay_dirty:
            return
        self._overlay_dirty = False
        if self.store is None or self.image_rgb is None:
            self._overlay = None
            return
        labels = self.store.labels
        if labels.size == 0 or not self.store.metas:
            self._overlay = None
            return
        max_id = max(self.store.next_id, int(labels.max()) + 1)
        code = np.zeros(max_id, np.uint8)
        for cid, meta in self.store.metas.items():
            if cid >= max_id:
                continue
            if meta.counted:
                code[cid] = 2
            elif meta.origin == "manual":
                code[cid] = 3
            else:
                code[cid] = 1
        status = code[labels]
        if self.preview_ids:
            preview = np.zeros(max_id, np.uint8)
            valid = [i for i in self.preview_ids if 0 < i < max_id]
            if valid:
                preview[np.asarray(valid, dtype=np.int64)] = 1
            status = np.where(preview[labels] > 0, 4, status)

        def _rgb(color):
            return [color.red(), color.green(), color.blue()]

        preview_color = QColor(theme.BLUE)
        fill_lut = np.array([
            [0, 0, 0],
            _rgb(self.style.auto_fill),
            _rgb(self.style.counted_fill),
            _rgb(self.style.manual_fill),
            _rgb(preview_color),
        ], np.uint8)
        edge_lut = np.array([
            [0, 0, 0],
            _rgb(self.style.auto_edge),
            _rgb(self.style.counted_edge),
            _rgb(self.style.manual_edge),
            _rgb(preview_color),
        ], np.uint8)
        rgb = fill_lut[status]
        if self.fill_cells:
            fill_alpha = int(round(self.style.fill_opacity * 255 / 100))
            alpha = np.where(status > 0, fill_alpha, 0).astype(np.uint8)
        else:
            alpha = np.zeros(status.shape, np.uint8)

        edge = np.zeros(labels.shape, bool)
        edge[:-1, :] |= labels[:-1, :] != labels[1:, :]
        edge[:, :-1] |= labels[:, :-1] != labels[:, 1:]
        edge[-1, :] |= labels[-1, :] != 0
        edge[:, -1] |= labels[:, -1] != 0
        width = max(1, int(self.style.edge_width))
        if width > 1:
            edge = cv2.dilate(edge.astype(np.uint8),
                              np.ones((width, width), np.uint8),
                              iterations=1).astype(bool)
        st_max = np.maximum.reduce([
            status,
            np.roll(status, 1, 0), np.roll(status, -1, 0),
            np.roll(status, 1, 1), np.roll(status, -1, 1),
        ])
        rgb[edge] = edge_lut[st_max[edge]]
        alpha[edge] = int(round(self.style.edge_opacity * 255 / 100))

        rgba = np.dstack([rgb, alpha])
        h, w = labels.shape
        self._overlay = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888).copy()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.BG_DEEP))
        if self._qimage is None:
            p.setPen(QColor(theme.TEXT_MUTED))
            f = QFont(theme.FONT_FAMILY, 12)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, i18n.translate(
                "打开一张 DAPI / WGS 图像\n或使用“文件 → 打开图像”"))
            p.end()
            return

        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self._image_size()
        target = QRectF(self.ox, self.oy, w * self.scale, h * self.scale)
        p.drawImage(target, self._qimage)

        self._ensure_overlay()
        if self._overlay is not None and self.overlay_opacity > 0:
            p.setOpacity(self.overlay_opacity)
            p.drawImage(target, self._overlay)
            p.setOpacity(1.0)

        # hover / selected outlines
        if self.store is not None:
            if self.hover_id is not None and self.hover_id not in self.selected:
                self._draw_contour(p, self.hover_id,
                                   QPen(QColor(255, 255, 255, 210), 1.2),
                                   dash=False)
            for cid in list(self.selected)[:200]:
                self._draw_contour(p, cid,
                                   QPen(QColor(theme.CYAN), 2.0, Qt.DashLine),
                                   dash=True)

            if self.show_labels:
                self._draw_labels(p)

        if self._drag == "draw" and len(self._draw_points) >= 2:
            self._draw_preview_polygon(p)
        if self._box_rect is not None:
            self._draw_box_preview(p)
        self._draw_calibration(p)

        p.end()

    def _draw_contour(self, p: QPainter, cid: int, pen: QPen, dash: bool):
        if self.store is None:
            return
        st = self.store.stats.get(cid)
        if st is None:
            return
        r0, r1, c0, c1 = st.bbox
        sub = (self.store.labels[r0:r1, c0:c1] == cid).astype(np.uint8)
        if sub.size == 0:
            return
        contours, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        for cnt in contours:
            if len(cnt) < 3:
                continue
            pts = []
            for xy in cnt[:, 0, :]:
                sx, sy = self.image_to_screen(c0 + float(xy[0]) + 0.5,
                                              r0 + float(xy[1]) + 0.5)
                pts.append(QPointF(sx, sy))
            p.drawPolygon(QPolygonF(pts))

    def _draw_labels(self, p: QPainter):
        if self.store is None:
            return
        numbers = self.store.number_map()
        if not numbers:
            return
        if self.scale < 0.3 and len(numbers) > 150:
            return
        font = QFont(theme.MONO_FAMILY, 8)
        font.setBold(True)
        p.setFont(font)
        p.setRenderHint(QPainter.Antialiasing, True)
        for cid, num in numbers.items():
            st = self.store.stats.get(cid)
            if st is None:
                continue
            sx, sy = self.image_to_screen(st.cx, st.cy)
            if sx < -20 or sy < -20 or sx > self.width() + 20 or sy > self.height() + 20:
                continue
            text = str(num)
            r = 8 if len(text) <= 3 else 10
            p.setBrush(QBrush(QColor(6, 12, 24, 190)))
            p.setPen(QPen(QColor(250, 204, 21, 220), 1))
            p.drawEllipse(QPointF(sx, sy), r, r)
            p.setPen(QColor(255, 255, 255))
            p.drawText(QRectF(sx - 12, sy - 8, 24, 16), Qt.AlignCenter, text)

    def _draw_preview_polygon(self, p: QPainter):
        pts = [QPointF(*self.image_to_screen(x, y)) for x, y in self._draw_points]
        path = QPainterPath(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        if len(pts) >= 3:
            path.lineTo(pts[0])
        p.setBrush(QBrush(QColor(34, 211, 238, 45)))
        p.setPen(QPen(QColor(theme.CYAN), 2.0, Qt.DashLine))
        p.drawPath(path)

    def _draw_box_preview(self, p: QPainter):
        color = QColor(theme.CYAN)
        if self._box_kind == "delete":
            color = QColor(theme.DANGER)
        elif self._box_kind == "uncount":
            color = QColor(theme.ORANGE)
        elif self._box_kind == "count":
            color = QColor(theme.ACCENT)
        p.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 36)))
        p.setPen(QPen(color, 1.6, Qt.DashLine))
        p.drawRect(self._box_rect)
