"""Dialog for customising overlay colours, opacity and edge width."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox, QColorDialog, QDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from . import i18n, theme
from .overlay_style import OverlayStyle


class ColorButton(QPushButton):
    colorChanged = pyqtSignal(QColor)

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedHeight(28)
        self.setMinimumWidth(104)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("点击选择颜色")
        self._refresh()
        self.clicked.connect(self._pick)

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor, emit: bool = False):
        color = QColor(color)
        if not color.isValid():
            return
        self._color = color
        self._refresh()
        if emit:
            self.colorChanged.emit(QColor(color))

    def _refresh(self):
        r, g, b, _ = self._color.getRgb()
        luminance = (r * 299 + g * 587 + b * 114) / 1000.0
        text = "#000000" if luminance > 155 else "#FFFFFF"
        self.setText(self._color.name().upper())
        self.setStyleSheet(
            "QPushButton {"
            f"background:{self._color.name()};color:{text};"
            "border:1px solid #475569;border-radius:6px;"
            "font-family:Consolas;font-size:11px;font-weight:600;padding:3px 6px;"
            "}"
            "QPushButton:hover {border:1px solid #E2E8F0;}"
        )

    def _pick(self):
        color = QColorDialog.getColor(self._color, self, i18n.translate("选择颜色"))
        if color.isValid():
            self.set_color(color, emit=True)


class StyleDialog(QDialog):
    styleChanged = pyqtSignal(object)

    STATE_ROWS = (
        ("counted", "已计数"),
        ("auto", "未计数 · 自动"),
        ("manual", "未计数 · 手动"),
    )

    def __init__(self, style: OverlayStyle, parent=None):
        super().__init__(parent)
        self.style = style.copy()
        self.setWindowTitle("显示样式")
        self.setMinimumWidth(560)
        self.setModal(False)
        self.setStyleSheet(theme.STYLESHEET)

        self.edge_buttons: dict[str, ColorButton] = {}
        self.fill_buttons: dict[str, ColorButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        title = QLabel("显示样式")
        title.setObjectName("appTitle")
        root.addWidget(title)
        subtitle = QLabel(
            "调整会立即生效；可以继续缩放、标注和操作主窗口。"
            "默认边缘和填充同色，取消联动后可分开设置；关闭后自动保存。")
        subtitle.setObjectName("hint")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        headers = ("状态", "边缘颜色", "填充颜色")
        for col, text in enumerate(headers):
            lab = QLabel(text)
            lab.setObjectName("dim")
            grid.addWidget(lab, 0, col)
        for row, (key, label) in enumerate(self.STATE_ROWS, start=1):
            lab = QLabel(label)
            lab.setObjectName("hint")
            edge = ColorButton(self.style.edge_color(key))
            fill = ColorButton(self.style.fill_color(key))
            edge.colorChanged.connect(
                lambda color, k=key: self._on_color(k, "edge", color))
            fill.colorChanged.connect(
                lambda color, k=key: self._on_color(k, "fill", color))
            self.edge_buttons[key] = edge
            self.fill_buttons[key] = fill
            grid.addWidget(lab, row, 0)
            grid.addWidget(edge, row, 1)
            grid.addWidget(fill, row, 2)
        root.addLayout(grid)

        self.chk_link = QCheckBox("边缘和填充颜色联动（默认）")
        linked = all(
            self.style.edge_color(key).name() == self.style.fill_color(key).name()
            for key, _ in self.STATE_ROWS)
        self.chk_link.setChecked(linked)
        self.chk_link.toggled.connect(self._on_link_toggled)
        root.addWidget(self.chk_link)

        self.chk_fill = QCheckBox("填充细胞内部（关闭则只显示边缘）")
        self.chk_fill.setChecked(bool(self.style.fill_enabled))
        self.chk_fill.toggled.connect(self._on_fill_enabled)
        root.addWidget(self.chk_fill)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color:{theme.BORDER_SOFT};")
        root.addWidget(line)

        edge_row, self.edge_slider, self.edge_value = self._opacity_row(
            "边缘透明度", self.style.edge_opacity, self._set_edge_opacity)
        fill_row, self.fill_slider, self.fill_value = self._opacity_row(
            "填充透明度", self.style.fill_opacity, self._set_fill_opacity)
        root.addWidget(edge_row)
        root.addWidget(fill_row)

        width_row = QWidget()
        wh = QHBoxLayout(width_row)
        wh.setContentsMargins(0, 0, 0, 0)
        wh.setSpacing(10)
        wl = QLabel("边缘粗细")
        wl.setFixedWidth(86)
        wl.setObjectName("hint")
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 8)
        self.spin_width.setValue(self.style.edge_width)
        self.spin_width.setSuffix(" px")
        self.spin_width.valueChanged.connect(self._set_edge_width)
        wh.addWidget(wl)
        wh.addWidget(self.spin_width)
        wh.addStretch(1)
        root.addWidget(width_row)

        hint = QLabel("提示：勾选“填充细胞内部”后才会显示半透明填充；边缘粗细按图像像素计算。")
        hint.setObjectName("dim")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addStretch(1)

        buttons = QHBoxLayout()
        self.btn_reset = QPushButton("恢复默认")
        self.btn_close = QPushButton("关闭")
        self.btn_reset.clicked.connect(self._reset)
        self.btn_close.clicked.connect(self.accept)
        buttons.addWidget(self.btn_reset)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        root.addLayout(buttons)

    def _opacity_row(self, label: str, value: int, callback):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        lab = QLabel(label)
        lab.setFixedWidth(86)
        lab.setObjectName("hint")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(value))
        val = QLabel(f"{int(value)}%")
        val.setFixedWidth(40)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setObjectName("dim")
        slider.valueChanged.connect(callback)
        h.addWidget(lab)
        h.addWidget(slider, 1)
        h.addWidget(val)
        return row, slider, val

    # ------------------------------------------------------------- callbacks
    def _emit(self):
        self.styleChanged.emit(self.style.copy())

    def _on_color(self, key: str, part: str, color: QColor):
        setattr(self.style, f"{key}_{part}", QColor(color))
        if self.chk_link.isChecked():
            other = "fill" if part == "edge" else "edge"
            setattr(self.style, f"{key}_{other}", QColor(color))
            button = (self.fill_buttons if other == "fill" else self.edge_buttons)[key]
            button.set_color(color)
        self._emit()

    def _on_link_toggled(self, on: bool):
        if not on:
            return
        for key, _ in self.STATE_ROWS:
            color = self.style.edge_color(key)
            setattr(self.style, f"{key}_fill", QColor(color))
            self.fill_buttons[key].set_color(color)
        self._emit()

    def _set_edge_opacity(self, value: int):
        self.style.edge_opacity = int(value)
        self.edge_value.setText(f"{int(value)}%")
        self._emit()

    def _set_fill_opacity(self, value: int):
        self.style.fill_opacity = int(value)
        self.fill_value.setText(f"{int(value)}%")
        self._emit()

    def _set_edge_width(self, value: int):
        self.style.edge_width = int(value)
        self._emit()

    def _on_fill_enabled(self, on: bool):
        self.style.fill_enabled = bool(on)
        self._emit()

    def _reset(self):
        self.style = OverlayStyle()
        for key, _ in self.STATE_ROWS:
            self.edge_buttons[key].set_color(self.style.edge_color(key))
            self.fill_buttons[key].set_color(self.style.fill_color(key))
        self.chk_link.blockSignals(True)
        self.chk_link.setChecked(True)
        self.chk_link.blockSignals(False)
        self.chk_fill.blockSignals(True)
        self.chk_fill.setChecked(bool(self.style.fill_enabled))
        self.chk_fill.blockSignals(False)
        self.edge_slider.blockSignals(True)
        self.edge_slider.setValue(self.style.edge_opacity)
        self.edge_slider.blockSignals(False)
        self.edge_value.setText(f"{self.style.edge_opacity}%")
        self.fill_slider.blockSignals(True)
        self.fill_slider.setValue(self.style.fill_opacity)
        self.fill_slider.blockSignals(False)
        self.fill_value.setText(f"{self.style.fill_opacity}%")
        self.spin_width.blockSignals(True)
        self.spin_width.setValue(self.style.edge_width)
        self.spin_width.blockSignals(False)
        self._emit()
