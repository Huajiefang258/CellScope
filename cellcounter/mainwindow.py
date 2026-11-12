"""Main application window."""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PyQt5.QtCore import QEvent, QProcess, QProcessEnvironment, QSize, Qt, QTimer, QUrl
from PyQt5.QtGui import (
    QColor, QDesktopServices, QFont, QIcon, QPainter, QPalette, QPixmap,
)
from PyQt5.QtWidgets import (
    QAction, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget, QShortcut,
)

from . import i18n, theme
from .batch import BatchItem, BatchListWidget
from .imagej import (
    find_imagej, prepare_measurement, write_annotation_image, write_area_csv,
    write_label_image,
)
from .imaging import IMAGE_EXTENSIONS, LoadedImage, load_image
from .model import CellStore
from .models_info import (
    MODEL_CHOICES, MODEL_FILES, MODEL_HINTS, MODEL_LABELS, MODELS_DIR,
    RECOMMENDED_MODEL,
)
from .overlay_style import OverlayStyle
from .random_dialog import RandomSelectDialog
from .style_dialog import StyleDialog
from .viewer import ImageViewer

APP_ROOT = Path(__file__).resolve().parent.parent
TEMP_ROOT = APP_ROOT / ".tmp"

MODE1_HELP = """
<div style="line-height:150%">
<span style="color:#94A3B8;">适合 Cellpose 检出较准确、只需少量删改的情况。编号按从上到下、从左到右排列。切换模式不会清除现有标注；可用下方按钮统一计数状态。</span>
<ul style="margin-left:-18px;color:#94A3B8;">
<li><b style="color:#E8EEF7;">左键拖动</b>　手动绘制新细胞（立即计数）</li>
<li><b style="color:#E8EEF7;">左键点击</b>　选中细胞并查看信息</li>
<li><b style="color:#E8EEF7;">Ctrl + 点击</b>　取消 / 恢复计数</li>
<li><b style="color:#E8EEF7;">Alt + 点击 / 拖动</b>　删除细胞</li>
<li><b style="color:#E8EEF7;">Delete</b>　删除选中的细胞</li>
</ul>
</div>
"""

MODE2_HELP = """
<div style="line-height:150%">
<span style="color:#94A3B8;">Cellpose 结果先全部保留但不计数，由你逐个确认。编号按从上到下、从左到右排列。切换模式不会清除现有标注；可用下方按钮统一计数状态。</span>
<ul style="margin-left:-18px;color:#94A3B8;">
<li><b style="color:#E8EEF7;">左键点击</b>　计数 / 取消计数（颜色见上方图例）</li>
<li><b style="color:#E8EEF7;">左键拖动</b>　框选并计数</li>
<li><b style="color:#E8EEF7;">Ctrl + 拖动</b>　框选并取消计数</li>
<li><b style="color:#E8EEF7;">Shift + 左键拖动</b>　绘制新细胞（立即计数；取消计数后保留轮廓）</li>
<li><b style="color:#E8EEF7;">随机选细胞…</b>　空间均匀随机选取；蓝色预览，Enter 确认计数</li>
<li><b style="color:#E8EEF7;">Alt + 点击 / 拖动</b>　删除标注</li>
</ul>
</div>
"""

GLOBAL_HELP = """
<div style="color:#94A3B8;line-height:150%">
<b style="color:#E8EEF7;">视图</b>　滚轮缩放 · 中键拖动平移 · F 适应<br>
<b style="color:#E8EEF7;">编辑</b>　Ctrl+Z 撤销 · Ctrl+Y 重做 · Esc 取消<br>
<b style="color:#E8EEF7;">流程</b>　Ctrl+R 运行 · Ctrl+E 测量<br>
<span style="color:#64748B;">重新运行 Cellpose 时，模式一会自动全部计数，模式二默认全部不计数。</span>
</div>
"""

MODE1_HELP_EN = """
<div style="line-height:150%">
<span style="color:#94A3B8;">Best when Cellpose detection is accurate and only a few cells need editing. Numbers run top-to-bottom, left-to-right. Switching modes keeps labels; use the button below to unify count states.</span>
<ul style="margin-left:-18px;color:#94A3B8;">
<li><b style="color:#E8EEF7;">Left drag</b>　Draw a new cell (counted immediately)</li>
<li><b style="color:#E8EEF7;">Left click</b>　Select a cell and show its info</li>
<li><b style="color:#E8EEF7;">Ctrl + click</b>　Uncount / restore count</li>
<li><b style="color:#E8EEF7;">Alt + click / drag</b>　Delete cells</li>
<li><b style="color:#E8EEF7;">Delete</b>　Delete selected cells</li>
</ul>
</div>
"""

MODE2_HELP_EN = """
<div style="line-height:150%">
<span style="color:#94A3B8;">Cellpose results are kept but not counted; confirm each cell yourself. Numbers run top-to-bottom, left-to-right. Switching modes keeps labels; use the button below to unify count states.</span>
<ul style="margin-left:-18px;color:#94A3B8;">
<li><b style="color:#E8EEF7;">Left click</b>　Count / uncount (see legend above)</li>
<li><b style="color:#E8EEF7;">Left drag</b>　Box-select and count</li>
<li><b style="color:#E8EEF7;">Ctrl + drag</b>　Box-select and uncount</li>
<li><b style="color:#E8EEF7;">Shift + left drag</b>　Draw a new cell (counted; outline kept when uncounted)</li>
<li><b style="color:#E8EEF7;">Random select…</b>　Spatially spread random selection; blue preview, Enter to count</li>
<li><b style="color:#E8EEF7;">Alt + click / drag</b>　Delete labels</li>
</ul>
</div>
"""

GLOBAL_HELP_EN = """
<div style="color:#94A3B8;line-height:150%">
<b style="color:#E8EEF7;">View</b>　Wheel zoom · middle-drag pan · F fit<br>
<b style="color:#E8EEF7;">Edit</b>　Ctrl+Z undo · Ctrl+Y redo · Esc cancel<br>
<b style="color:#E8EEF7;">Flow</b>　Ctrl+R run · Ctrl+E measure<br>
<span style="color:#64748B;">Re-running Cellpose counts all cells in Mode 1 and leaves all uncounted in Mode 2.</span>
</div>
"""


class ResultsDialog(QDialog):
    def __init__(self, rows, csv_path: Path, out_dir: Path, unit: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ImageJ 面积测量结果")
        self.resize(680, 620)
        self.setStyleSheet(theme.STYLESHEET)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(12)

        title = QLabel("ImageJ 测量完成")
        title.setObjectName("appTitle")
        lay.addWidget(title)
        if i18n.get_language() == i18n.EN:
            info_text = (
                f"Exported areas for cells 1 – {len(rows)}.<br>"
                f"<span style='color:#94A3B8;'>Results table:</span>"
                f"<span style='color:#22D3EE;'>{csv_path}</span>")
        else:
            info_text = (
                f"已按细胞编号 1 – {len(rows)} 导出面积。<br>"
                f"<span style='color:#94A3B8;'>结果表格：</span>"
                f"<span style='color:#22D3EE;'>{csv_path}</span>")
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setObjectName("hint")
        lay.addWidget(info)

        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["细胞编号", f"面积 ({unit})"])
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 160)
        for r, (num, area) in enumerate(rows):
            a = QTableWidgetItem(f"{float(area):.3f}")
            a.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            n = QTableWidgetItem(str(num))
            n.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, 0, n)
            table.setItem(r, 1, a)
        lay.addWidget(table, 1)

        btns = QHBoxLayout()
        btn_csv = QPushButton("打开 CSV")
        btn_csv.setObjectName("primary")
        btn_csv.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(csv_path))))
        btn_dir = QPushButton("打开结果文件夹")
        btn_dir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(out_dir))))
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_csv)
        btns.addWidget(btn_dir)
        btns.addStretch(1)
        btns.addWidget(btn_close)
        lay.addLayout(btns)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.setWindowTitle("SimpleCellSegmentation · Cellpose + ImageJ 细胞计数")
        self.resize(1500, 960)
        self.setMinimumSize(1120, 720)
        self.setAcceptDrops(True)
        self.setWindowIcon(self._make_icon())

        self.loaded: LoadedImage | None = None
        self.store = CellStore()
        self.mode = 1
        self.style = OverlayStyle.load()
        self.pending_random_ids: list[int] | None = None
        self.style_dialog: StyleDialog | None = None
        self._calibration_real_um: float | None = None
        self.batch_items: dict[int, BatchItem] = {}
        self.batch_order: list[int] = []
        self.batch_next_id = 1
        self.batch_dir: Path | None = None
        self.batch_proc: QProcess | None = None
        self.batch_processing_id: int | None = None
        self.batch_buf = ""
        self.batch_log = ""
        self.batch_done_payload: dict | None = None
        self.batch_error = ""
        self.batch_stage = ""
        self.batch_current_loaded_id: int | None = None
        self.batch_autoload_first = False
        self.calib_timer = QTimer(self)
        self.calib_timer.setSingleShot(True)
        self.calib_timer.timeout.connect(self._clear_calibration_display)
        self.lang_timer = QTimer(self)
        self.lang_timer.setInterval(400)
        self.lang_timer.timeout.connect(self._localize_runtime)
        self.out_dir: Path | None = None
        self.last_results: tuple[Path, Path] | None = None

        self.cp_proc: QProcess | None = None
        self.cp_buf = ""
        self.cp_log = ""
        self.cp_done_payload: dict | None = None
        self.cp_error = ""
        self.cp_cancelled = False

        self.dl_proc: QProcess | None = None
        self.dl_buf = ""
        self.dl_ok = False

        self.ij_proc: QProcess | None = None
        self.ij_buf = ""
        self.ij_log = ""
        self.ij_rows: list[tuple[int, float]] = []
        self.ij_version = ""
        self.ij_setup = None
        self.ij_snapshot_mask = None
        self.ij_snapshot_display = None
        self.ij_cancelled = False
        self.ij_done = False

        self._build_ui()
        self._build_actions()
        self._on_model_changed(0)
        self._set_mode(1, initial=True)
        self._update_ui()
        self.viewer.set_store(self.store)
        QApplication.instance().installEventFilter(self)
        self._apply_language(initial=True)

    # --------------------------------------------------------------- UI build
    def _make_icon(self) -> QIcon:
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setBrush(QColor(theme.ACCENT))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(2, 2, 60, 60, 15, 15)
        p.setBrush(QColor(theme.BG))
        p.drawEllipse(13, 14, 24, 18)
        p.drawEllipse(30, 30, 20, 16)
        p.setBrush(QColor(theme.YELLOW))
        p.drawEllipse(19, 19, 6, 6)
        p.drawEllipse(36, 35, 6, 6)
        p.end()
        return QIcon(pm)

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(2)
        split.addWidget(self._scroll_panel(self._build_left_panel(), 330))
        split.addWidget(self._build_center())
        split.addWidget(self._scroll_panel(self._build_right_panel(), 340))
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setStretchFactor(2, 0)
        split.setSizes([380, 760, 350])

        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(14, 12, 14, 10)
        wl.setSpacing(0)
        wl.addWidget(split)
        root.addWidget(wrap, 1)

        self.setCentralWidget(central)

    def _scroll_panel(self, widget, width):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        pal = scroll.viewport().palette()
        pal.setColor(QPalette.Window, QColor(theme.BG))
        pal.setColor(QPalette.Base, QColor(theme.BG))
        scroll.viewport().setPalette(pal)
        scroll.viewport().setAutoFillBackground(True)
        panel_pal = widget.palette()
        panel_pal.setColor(QPalette.Window, QColor(theme.BG))
        panel_pal.setColor(QPalette.Base, QColor(theme.BG))
        widget.setPalette(panel_pal)
        widget.setAutoFillBackground(True)
        scroll.setWidget(widget)
        scroll.setMinimumWidth(300)
        scroll.setMaximumWidth(430)
        widget.setMinimumWidth(0)
        return scroll

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(66)
        lay = QHBoxLayout(header)
        lay.setContentsMargins(18, 8, 18, 8)
        lay.setSpacing(12)

        logo = QLabel()
        logo.setPixmap(self._make_icon().pixmap(38, 38))
        logo.setFixedSize(38, 38)
        lay.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("SimpleCS")
        t.setToolTip("SimpleCellSegmentation")
        t.setObjectName("appTitle")
        s = QLabel("Cellpose 自动标注 · 人工校正 · ImageJ 面积测量")
        s.setObjectName("appSubtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        lay.addLayout(titles)
        lay.addStretch(1)

        self.btn_style_header = QPushButton("显示样式")
        self.btn_style_header.setObjectName("ghost")
        self.btn_style_header.setToolTip("打开非模态实时样式面板")
        self.btn_style_header.clicked.connect(self.open_style_dialog)
        self.btn_batch = QPushButton("批量处理")
        self.btn_batch.setObjectName("ghost")
        self.btn_batch.setToolTip("选择多张图像加入批量队列")
        self.btn_batch.clicked.connect(self.choose_batch_files)
        self.btn_open = QPushButton("打开图像")
        self.btn_open.setToolTip("打开 TIFF / PNG / JPEG 图像 (Ctrl+O)")
        self.btn_open.clicked.connect(self.open_image_dialog)
        self.btn_help = QPushButton("操作说明")
        self.btn_help.setObjectName("ghost")
        self.btn_help.clicked.connect(self.show_shortcuts)
        self.btn_lang = QPushButton("English")
        self.btn_lang.setObjectName("ghost")
        self.btn_lang.setToolTip("切换到 English")
        self.btn_lang.clicked.connect(self.toggle_language)
        lay.addWidget(self.btn_style_header)
        lay.addWidget(self.btn_batch)
        lay.addWidget(self.btn_open)
        lay.addWidget(self.btn_help)
        lay.addWidget(self.btn_lang)
        return header

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.setSpacing(9)
        lab = QLabel(title)
        lab.setObjectName("cardTitle")
        lay.addWidget(lab)
        return card, lay

    def _form_row(self, label: str, widget: QWidget) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        lab = QLabel(label)
        lab.setObjectName("hint")
        lab.setFixedWidth(72)
        h.addWidget(lab)
        h.addWidget(widget, 1)
        return row

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # ---- image card
        card, cl = self._card("1 · 图像与显示")
        self.btn_open_2 = QPushButton("打开图像…    Ctrl+O")
        self.btn_open_2.clicked.connect(self.open_image_dialog)
        cl.addWidget(self.btn_open_2)
        self.lbl_file = QLabel("尚未载入图像")
        self.lbl_file.setObjectName("hint")
        self.lbl_file.setWordWrap(True)
        cl.addWidget(self.lbl_file)
        self.lbl_image_info = QLabel("")
        self.lbl_image_info.setObjectName("dim")
        cl.addWidget(self.lbl_image_info)
        self.combo_display = QComboBox()
        self.combo_display.addItem("复合显示", "composite")
        self.combo_display.currentIndexChanged.connect(self._on_display_changed)
        cl.addWidget(self._form_row("显示", self.combo_display))
        self.lbl_warning = QLabel("")
        self.lbl_warning.setWordWrap(True)
        self.lbl_warning.setStyleSheet(f"color:{theme.ORANGE};font-size:11px;")
        self.lbl_warning.hide()
        cl.addWidget(self.lbl_warning)
        lay.addWidget(card)

        # ---- cellpose card
        card, cl = self._card("2 · Cellpose 自动标注")
        self.combo_model = QComboBox()
        for key in MODEL_CHOICES:
            self.combo_model.addItem(MODEL_LABELS[key], key)
        self.combo_model.setToolTip("推荐 cyto3；其他模型可在界面中下载后切换使用。")
        self.combo_model.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_model.setMinimumContentsLength(8)
        self.combo_model.currentIndexChanged.connect(self._on_model_changed)
        cl.addWidget(self._form_row("模型", self.combo_model))
        self.lbl_model_hint = QLabel(MODEL_HINTS[RECOMMENDED_MODEL])
        self.lbl_model_hint.setObjectName("dim")
        self.lbl_model_hint.setWordWrap(True)
        cl.addWidget(self.lbl_model_hint)

        self.combo_source = QComboBox()
        self.combo_source.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_source.setMinimumContentsLength(8)
        self.combo_source.addItem("自动（膜 / 通道 2）", ("auto", 0))
        cl.addWidget(self._form_row("分割来源", self.combo_source))

        dia = QWidget()
        dh = QHBoxLayout(dia)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(8)
        self.chk_auto_dia = QCheckBox("自动")
        self.chk_auto_dia.setChecked(True)
        self.spin_dia = QSpinBox()
        self.spin_dia.setRange(5, 1000)
        self.spin_dia.setValue(30)
        self.spin_dia.setSuffix(" px")
        self.spin_dia.setEnabled(False)
        self.chk_auto_dia.toggled.connect(
            lambda on: self.spin_dia.setEnabled(not on))
        dh.addWidget(self.chk_auto_dia)
        dh.addWidget(self.spin_dia, 1)
        cl.addWidget(self._form_row("直径", dia))

        self.btn_adv = QToolButton()
        self.btn_adv.setText("高级参数")
        self.btn_adv.setCheckable(True)
        self.btn_adv.setToolTip("流阈值、细胞概率阈值、最小面积")
        self.btn_adv.toggled.connect(self._toggle_advanced)
        cl.addWidget(self.btn_adv)
        self.advanced = QWidget()
        al = QVBoxLayout(self.advanced)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(7)
        self.spin_flow = QDoubleSpinBox()
        self.spin_flow.setRange(0.0, 2.0)
        self.spin_flow.setSingleStep(0.05)
        self.spin_flow.setDecimals(2)
        self.spin_flow.setValue(0.40)
        self.spin_cellprob = QDoubleSpinBox()
        self.spin_cellprob.setRange(-6.0, 6.0)
        self.spin_cellprob.setSingleStep(0.5)
        self.spin_cellprob.setDecimals(1)
        self.spin_cellprob.setValue(0.0)
        self.spin_min = QSpinBox()
        self.spin_min.setRange(0, 100000)
        self.spin_min.setValue(15)
        self.spin_min.setSuffix(" px")
        al.addWidget(self._form_row("流阈值", self.spin_flow))
        al.addWidget(self._form_row("细胞概率", self.spin_cellprob))
        al.addWidget(self._form_row("最小面积", self.spin_min))
        self.advanced.hide()
        cl.addWidget(self.advanced)

        self.btn_run_cp = QPushButton("运行 Cellpose 标注    Ctrl+R")
        self.btn_run_cp.setObjectName("primary")
        self.btn_run_cp.clicked.connect(self.run_cellpose)
        cl.addWidget(self.btn_run_cp)

        row = QHBoxLayout()
        self.progress_cp = QProgressBar()
        self.progress_cp.setRange(0, 0)
        self.progress_cp.setTextVisible(False)
        self.progress_cp.hide()
        self.btn_cancel_cp = QPushButton("取消")
        self.btn_cancel_cp.setObjectName("ghost")
        self.btn_cancel_cp.clicked.connect(self.cancel_cellpose)
        self.btn_cancel_cp.hide()
        row.addWidget(self.progress_cp, 1)
        row.addWidget(self.btn_cancel_cp)
        cl.addLayout(row)

        self.lbl_cp_status = QLabel("模型会先检测细胞，再为每个细胞编号。")
        self.lbl_cp_status.setObjectName("dim")
        self.lbl_cp_status.setWordWrap(True)
        cl.addWidget(self.lbl_cp_status)

        self.btn_model = QPushButton("检查 / 下载当前模型")
        self.btn_model.setObjectName("ghost")
        self.btn_model.clicked.connect(self.check_model)
        cl.addWidget(self.btn_model)
        self.lbl_model_note = QLabel("模型不随程序打包；推荐下载 cyto3（快速、通用）。")
        self.lbl_model_note.setObjectName("dim")
        self.lbl_model_note.setWordWrap(True)
        cl.addWidget(self.lbl_model_note)
        lay.addWidget(card)

        # ---- imagej card
        card, cl = self._card("3 · ImageJ 面积测量")
        self.spin_pixel = QDoubleSpinBox()
        self.spin_pixel.setRange(0.0, 100000.0)
        self.spin_pixel.setDecimals(6)
        self.spin_pixel.setSingleStep(0.01)
        self.spin_pixel.setValue(0.0)
        self.spin_pixel.setSpecialValueText("未校准（按像素²）")
        self.spin_pixel.setSuffix(" µm/px")
        self.spin_pixel.setToolTip("设置 1 像素对应的物理尺寸；0 表示按像素²测量。")
        pixel_row = QWidget()
        ph = QHBoxLayout(pixel_row)
        ph.setContentsMargins(0, 0, 0, 0)
        ph.setSpacing(6)
        self.btn_calibrate = QPushButton("手动标定…")
        self.btn_calibrate.setObjectName("ghost")
        self.btn_calibrate.setToolTip("输入已知真实长度（如 20 µm），然后在图上点击两点")
        self.btn_calibrate.clicked.connect(self.start_calibration)
        ph.addWidget(self.spin_pixel, 1)
        ph.addWidget(self.btn_calibrate)
        cl.addWidget(self._form_row("像素尺寸", pixel_row))

        out_row = QWidget()
        oh = QHBoxLayout(out_row)
        oh.setContentsMargins(0, 0, 0, 0)
        oh.setSpacing(6)
        self.lbl_outdir = QLabel("载入图像后自动设置")
        self.lbl_outdir.setObjectName("dim")
        self.lbl_outdir.setWordWrap(True)
        btn_out = QPushButton("选择")
        btn_out.setObjectName("ghost")
        btn_out.clicked.connect(self.choose_output_dir)
        oh.addWidget(self.lbl_outdir, 1)
        oh.addWidget(btn_out)
        cl.addWidget(self._form_row("输出", out_row))

        self.btn_measure = QPushButton("测量并导出表格    Ctrl+E")
        self.btn_measure.setObjectName("primary")
        self.btn_measure.clicked.connect(self.run_imagej)
        cl.addWidget(self.btn_measure)
        self.btn_export_image = QPushButton("导出标注图像…    Ctrl+Shift+E")
        self.btn_export_image.setObjectName("ghost")
        self.btn_export_image.clicked.connect(self.export_annotated_image)
        cl.addWidget(self.btn_export_image)

        row = QHBoxLayout()
        self.progress_ij = QProgressBar()
        self.progress_ij.setRange(0, 0)
        self.progress_ij.setTextVisible(False)
        self.progress_ij.hide()
        self.btn_cancel_ij = QPushButton("取消")
        self.btn_cancel_ij.setObjectName("ghost")
        self.btn_cancel_ij.clicked.connect(self.cancel_imagej)
        self.btn_cancel_ij.hide()
        row.addWidget(self.progress_ij, 1)
        row.addWidget(self.btn_cancel_ij)
        cl.addLayout(row)

        self.lbl_ij_status = QLabel("测量只导出 CSV 表格；标注图像和标签图请用上方按钮单独导出。")
        self.lbl_ij_status.setObjectName("dim")
        self.lbl_ij_status.setWordWrap(True)
        cl.addWidget(self.lbl_ij_status)
        self.btn_results = QPushButton("打开上次结果文件夹")
        self.btn_results.setObjectName("ghost")
        self.btn_results.clicked.connect(self.open_last_results)
        self.btn_results.hide()
        cl.addWidget(self.btn_results)
        lay.addWidget(card)

        # ---- batch card
        card, cl = self._card("4 · 批量处理")
        hint = QLabel(
            "把多张图像拖到下方列表，自动排队标注。若当前没有打开图像，"
            "第一张完成后会自动载入；可以边校正边让其他图像继续在后台处理。"
            "每个文件使用加入队列时的 Cellpose 参数。")
        hint.setObjectName("dim")
        hint.setWordWrap(True)
        cl.addWidget(hint)
        self.batch_list = BatchListWidget()
        self.batch_list.filesDropped.connect(self.add_batch_files)
        self.batch_list.itemClicked.connect(self._on_batch_item_clicked)
        cl.addWidget(self.batch_list)
        row = QHBoxLayout()
        self.btn_add_batch = QPushButton("添加文件…")
        self.btn_add_batch.setObjectName("ghost")
        self.btn_add_batch.clicked.connect(self.choose_batch_files)
        self.btn_clear_batch = QPushButton("清空")
        self.btn_clear_batch.setObjectName("ghost")
        self.btn_clear_batch.clicked.connect(self.clear_batch)
        row.addWidget(self.btn_add_batch)
        row.addWidget(self.btn_clear_batch)
        row.addStretch(1)
        cl.addLayout(row)
        self.lbl_batch_status = QLabel("拖入图像或点击“添加文件”。")
        self.lbl_batch_status.setObjectName("dim")
        self.lbl_batch_status.setWordWrap(True)
        cl.addWidget(self.lbl_batch_status)
        lay.addWidget(card)
        lay.addStretch(1)
        return panel

    def _build_center(self) -> QWidget:
        center = QWidget()
        lay = QVBoxLayout(center)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        bar = QWidget()
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(2, 0, 2, 0)
        hl.setSpacing(6)
        self.btn_mode1 = QToolButton()
        self.btn_mode1.setText("全部计数")
        self.btn_mode1.setMinimumWidth(96)
        self.btn_mode1.setToolTip("模式一 · 自动全部计数")
        self.btn_mode1.setObjectName("segment")
        self.btn_mode1.setCheckable(True)
        self.btn_mode1.setChecked(True)
        self.btn_mode2 = QToolButton()
        self.btn_mode2.setText("逐个确认")
        self.btn_mode2.setMinimumWidth(96)
        self.btn_mode2.setToolTip("模式二 · 逐个确认计数")
        self.btn_mode2.setObjectName("segment")
        self.btn_mode2.setCheckable(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.btn_mode1, 1)
        self.mode_group.addButton(self.btn_mode2, 2)
        self.mode_group.buttonClicked.connect(
            lambda b: self._set_mode(self.mode_group.id(b)))
        hl.addWidget(self.btn_mode1)
        hl.addWidget(self.btn_mode2)
        hl.addSpacing(10)

        self.btn_undo = QToolButton()
        self.btn_undo.setText("↶")
        self.btn_undo.setFixedWidth(34)
        self.btn_undo.setToolTip("撤销 (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo)
        self.btn_redo = QToolButton()
        self.btn_redo.setText("↷")
        self.btn_redo.setFixedWidth(34)
        self.btn_redo.setToolTip("重做 (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.redo)
        hl.addWidget(self.btn_undo)
        hl.addWidget(self.btn_redo)

        self.btn_fit = QToolButton()
        self.btn_fit.setText("适应")
        self.btn_fit.setToolTip("适应窗口 (F)")
        self.btn_fit.clicked.connect(lambda: self.viewer.fit())
        self.btn_100 = QToolButton()
        self.btn_100.setText("1:1")
        self.btn_100.clicked.connect(lambda: self.viewer.reset_100())
        hl.addWidget(self.btn_fit)
        hl.addWidget(self.btn_100)

        self.btn_labels = QToolButton()
        self.btn_labels.setText("编号")
        self.btn_labels.setCheckable(True)
        self.btn_labels.setChecked(True)
        self.btn_labels.setToolTip("显示已计数细胞的编号")
        self.btn_labels.toggled.connect(self._on_labels_toggled)
        hl.addWidget(self.btn_labels)

        hl.addStretch(1)
        lay.addWidget(bar)

        self.lbl_random_confirm = QLabel("")
        self.lbl_random_confirm.setObjectName("banner")
        self.lbl_random_confirm.setWordWrap(True)
        self.lbl_random_confirm.hide()
        lay.addWidget(self.lbl_random_confirm)

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{border:1px solid #1E2B42;border-radius:12px;background:#070D18;}")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(1, 1, 1, 1)
        self.viewer = ImageViewer()
        self.viewer.set_style(self.style)
        self.viewer.set_fill_cells(self.style.fill_enabled)
        self.viewer.positionChanged.connect(self.lbl_position_set)
        self.viewer.zoomChanged.connect(self._on_zoom)
        self.viewer.editApplied.connect(self._on_edit)
        self.viewer.selectionChanged.connect(self._on_selection)
        self.viewer.modeRequested.connect(self._set_mode)
        self.viewer.calibrationFinished.connect(self._on_calibration_finished)
        self.viewer.calibrationCancelled.connect(self._on_calibration_cancelled)
        fl.addWidget(self.viewer)
        lay.addWidget(frame, 1)

        status = QWidget()
        sh = QHBoxLayout(status)
        sh.setContentsMargins(2, 0, 2, 0)
        sh.setSpacing(14)
        self.lbl_status = QLabel("先打开一张图像，然后运行 Cellpose 自动标注。")
        self.lbl_status.setObjectName("status")
        self.lbl_position = QLabel("")
        self.lbl_position.setObjectName("dim")
        self.lbl_counts = QLabel("")
        self.lbl_counts.setObjectName("dim")
        self.lbl_zoom = QLabel("")
        self.lbl_zoom.setObjectName("dim")
        sh.addWidget(self.lbl_status, 1)
        sh.addWidget(self.lbl_position)
        sh.addWidget(self.lbl_counts)
        sh.addWidget(self.lbl_zoom)
        lay.addWidget(status)
        return center

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card, cl = self._card("计数概览")
        big_row = QHBoxLayout()
        big = QLabel("0")
        big.setObjectName("bigNumber")
        big.setStyleSheet(f"color:{self.style.counted_edge.name()};")
        self.lbl_big = big
        txt = QVBoxLayout()
        txt.setSpacing(0)
        t1 = QLabel("已计数细胞")
        t1.setObjectName("hint")
        self.lbl_summary = QLabel("尚未运行 Cellpose")
        self.lbl_summary.setObjectName("dim")
        self.lbl_summary.setWordWrap(True)
        txt.addWidget(t1)
        txt.addWidget(self.lbl_summary)
        big_row.addWidget(big)
        big_row.addSpacing(10)
        big_row.addLayout(txt, 1)
        cl.addLayout(big_row)

        legend = QHBoxLayout()
        legend.setSpacing(10)
        self.legend_chips: dict[str, QLabel] = {}
        for key, text in (("counted", "已计数"),
                          ("auto", "未计数·自动"),
                          ("manual", "未计数·手动")):
            chip = QLabel()
            chip.setFixedSize(10, 10)
            self.legend_chips[key] = chip
            lab = QLabel(text)
            lab.setObjectName("dim")
            legend.addWidget(chip)
            legend.addWidget(lab)
        legend.addStretch(1)
        cl.addLayout(legend)
        self._refresh_legend()

        lay.addWidget(card)

        card, cl = self._card("当前模式")
        self.lbl_mode_title = QLabel("")
        self.lbl_mode_title.setObjectName("metric")
        self.lbl_mode_help = QLabel("")
        self.lbl_mode_help.setWordWrap(True)
        self.lbl_mode_help.setTextFormat(Qt.RichText)
        self.lbl_mode_help.setObjectName("hint")
        self.lbl_mode_help.setMinimumWidth(0)
        self.lbl_mode_help.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.btn_mode_reset = QPushButton("全部设为已计数")
        self.btn_mode_reset.setToolTip("按当前模式统一现有细胞的计数状态；不会删除标注，可撤销")
        self.btn_mode_reset.clicked.connect(self.reset_counts_for_mode)
        self.btn_random = QPushButton("随机选细胞…")
        self.btn_random.setToolTip("从候选细胞中空间均匀地随机选取指定数量")
        self.btn_random.clicked.connect(self.random_select_cells)
        self.btn_random.setVisible(False)
        cl.addWidget(self.lbl_mode_title)
        cl.addWidget(self.lbl_mode_help)
        cl.addWidget(self.btn_mode_reset)
        cl.addWidget(self.btn_random)
        cl.addWidget(QFrame())
        self.lbl_global_help = self._rich_help(GLOBAL_HELP)
        cl.addWidget(self.lbl_global_help)
        lay.addWidget(card)

        card, cl = self._card("已计数细胞")
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["编号", "面积 px²", "来源"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 58)
        self.table.setColumnWidth(1, 108)
        self.table.cellClicked.connect(self._on_table_click)
        self.table.cellDoubleClicked.connect(self._on_table_double)
        cl.addWidget(self.table, 1)
        self.lbl_table_hint = QLabel("双击一行可定位到对应细胞。")
        self.lbl_table_hint.setObjectName("dim")
        cl.addWidget(self.lbl_table_hint)
        lay.addWidget(card, 1)
        return panel

    def _rich_help(self, html: str) -> QLabel:
        lab = QLabel(html)
        lab.setWordWrap(True)
        lab.setTextFormat(Qt.RichText)
        lab.setObjectName("hint")
        lab.setMinimumWidth(0)
        lab.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        return lab

    # --------------------------------------------------------------- actions
    def _build_actions(self):
        self.act_open = QAction("打开图像…", self)
        self.act_open.setShortcut("Ctrl+O")
        self.act_open.triggered.connect(self.open_image_dialog)
        self.act_save = QAction("保存标注…", self)
        self.act_save.setShortcut("Ctrl+S")
        self.act_save.triggered.connect(self.save_session)
        self.act_load = QAction("载入标注…", self)
        self.act_load.setShortcut("Ctrl+Shift+O")
        self.act_load.triggered.connect(self.load_session)
        self.act_measure = QAction("测量并导出表格…", self)
        self.act_measure.setShortcut("Ctrl+E")
        self.act_measure.triggered.connect(self.run_imagej)
        self.act_export_image = QAction("导出标注图像…", self)
        self.act_export_image.setShortcut("Ctrl+Shift+E")
        self.act_export_image.triggered.connect(self.export_annotated_image)
        self.act_quit = QAction("退出", self)
        self.act_quit.setShortcut("Ctrl+Q")
        self.act_quit.triggered.connect(self.close)

        self.act_undo = QAction("撤销", self)
        self.act_undo.setShortcut("Ctrl+Z")
        self.act_undo.triggered.connect(self.undo)
        self.act_redo = QAction("重做", self)
        self.act_redo.setShortcut("Ctrl+Y")
        self.act_redo.triggered.connect(self.redo)
        self.act_delete = QAction("删除选中细胞", self)
        self.act_delete.triggered.connect(self.delete_selected)
        self.act_clear = QAction("清除全部标注…", self)
        self.act_clear.triggered.connect(self.clear_all)
        self.act_random = QAction("随机选细胞…（模式二）", self)
        self.act_random.triggered.connect(self.random_select_cells)
        self.act_mode_reset = QAction("全部设为已计数（模式一）", self)
        self.act_mode_reset.triggered.connect(self.reset_counts_for_mode)

        self.act_fit = QAction("适应窗口", self)
        self.act_fit.setShortcut("F")
        self.act_fit.triggered.connect(lambda: self.viewer.fit())
        self.act_100 = QAction("实际像素 1:1", self)
        self.act_100.triggered.connect(lambda: self.viewer.reset_100())
        self.act_labels = QAction("显示编号", self)
        self.act_labels.setCheckable(True)
        self.act_labels.setChecked(True)
        self.act_labels.toggled.connect(self._on_labels_toggled)
        self.act_help = QAction("操作说明", self)
        self.act_help.setShortcut("F1")
        self.act_help.triggered.connect(self.show_shortcuts)
        self.act_about = QAction("关于 SimpleCellSegmentation", self)
        self.act_about.triggered.connect(self.show_about)

        mb = self.menuBar()
        m = mb.addMenu("文件")
        m.addAction(self.act_open)
        m.addSeparator()
        m.addAction(self.act_save)
        m.addAction(self.act_load)
        m.addSeparator()
        m.addAction(self.act_measure)
        m.addAction(self.act_export_image)
        m.addSeparator()
        m.addAction(self.act_quit)
        m = mb.addMenu("编辑")
        m.addAction(self.act_undo)
        m.addAction(self.act_redo)
        m.addSeparator()
        m.addAction(self.act_delete)
        m.addAction(self.act_clear)
        m.addAction(self.act_random)
        m.addAction(self.act_mode_reset)
        m = mb.addMenu("视图")
        m.addAction(self.act_fit)
        m.addAction(self.act_100)
        m.addSeparator()
        m.addAction(self.act_labels)
        m = mb.addMenu("帮助")
        m.addAction(self.act_help)
        m.addAction(self.act_about)

        QShortcut("Ctrl+R", self, activated=self.run_cellpose)
        self.sc_confirm_return = QShortcut("Return", self)
        self.sc_confirm_enter = QShortcut("Enter", self)
        self.sc_cancel_random = QShortcut("Esc", self)
        for sc in (self.sc_confirm_return, self.sc_confirm_enter,
                   self.sc_cancel_random):
            sc.setEnabled(False)
        self.sc_confirm_return.activated.connect(self.confirm_pending_random)
        self.sc_confirm_enter.activated.connect(self.confirm_pending_random)
        self.sc_cancel_random.activated.connect(self.cancel_pending_random)

    # ------------------------------------------------------------- small slots
    def lbl_position_set(self, text: str):
        self.lbl_position.setText(text)

    def _on_zoom(self, scale: float):
        self.lbl_zoom.setText(f"缩放 {scale * 100:.0f}%")

    def _on_labels_toggled(self, on: bool):
        self.viewer.set_show_labels(on)
        for w in (self.btn_labels,):
            w.blockSignals(True)
            w.setChecked(on)
            w.blockSignals(False)
        self.act_labels.blockSignals(True)
        self.act_labels.setChecked(on)
        self.act_labels.blockSignals(False)

    def _on_model_changed(self, _index: int):
        model = self.combo_model.currentData()
        self.lbl_model_hint.setText(MODEL_HINTS.get(model, ""))
        self.btn_model.setText(f"检查 / 下载 {model}")

    def open_style_dialog(self):
        if self.style_dialog is not None and self.style_dialog.isVisible():
            self.style_dialog.raise_()
            self.style_dialog.activateWindow()
            return
        dlg = StyleDialog(self.style, self)
        dlg.setWindowFlag(Qt.Tool, True)
        dlg.styleChanged.connect(self._apply_live_style)
        dlg.finished.connect(self._on_style_dialog_closed)
        self.style_dialog = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _apply_live_style(self, style):
        self.style = style.copy()
        self.viewer.set_style(self.style)
        self.viewer.set_fill_cells(self.style.fill_enabled)
        self._refresh_style_visuals()

    def _on_style_dialog_closed(self, _result):
        self.style.save()
        self.style_dialog = None

    def _refresh_legend(self):
        if not hasattr(self, "legend_chips"):
            return
        for key, chip in self.legend_chips.items():
            color = self.style.edge_color(key).name()
            chip.setStyleSheet(
                f"background:{color};border-radius:5px;border:1px solid #334155;")

    def _refresh_style_visuals(self):
        self._refresh_legend()
        if hasattr(self, "lbl_big"):
            self.lbl_big.setStyleSheet(
                f"color:{self.style.counted_edge.name()};")

    def _refresh_mode_help(self):
        en = i18n.get_language() == i18n.EN
        if self.mode == 1:
            self.lbl_mode_title.setText(
                "Mode 1 · Count all" if en else "模式一 · 全部计数")
            self.lbl_mode_help.setText(MODE1_HELP_EN if en else MODE1_HELP)
        else:
            self.lbl_mode_title.setText(
                "Mode 2 · Confirm one by one" if en else "模式二 · 逐个确认")
            self.lbl_mode_help.setText(MODE2_HELP_EN if en else MODE2_HELP)
        if hasattr(self, "lbl_global_help"):
            self.lbl_global_help.setText(GLOBAL_HELP_EN if en else GLOBAL_HELP)

    def _update_language_button(self):
        en = i18n.get_language() == i18n.EN
        self.btn_lang.setText("中文" if en else "English")
        self.btn_lang.setToolTip(
            "Switch to Chinese" if en else "切换到 English")

    def toggle_language(self):
        i18n.set_language(i18n.EN if i18n.get_language() == i18n.ZH else i18n.ZH)
        self._apply_language()

    def _apply_language(self, initial: bool = False):
        lang = i18n.get_language()
        self._refresh_mode_help()
        self._update_ui()
        i18n.localize_tree(self)
        app = QApplication.instance()
        for w in app.topLevelWidgets():
            if w is not self:
                i18n.localize_tree(w)
        self._update_language_button()
        if lang == i18n.EN:
            self.lang_timer.start(400)
        else:
            self.lang_timer.stop()
        if not initial:
            self._set_status(
                "Interface language: English." if lang == i18n.EN
                else "界面语言：中文。")

    def _localize_runtime(self):
        if i18n.get_language() != i18n.EN:
            return
        i18n.localize_tree(self)
        app = QApplication.instance()
        for w in app.topLevelWidgets():
            if w is not self:
                i18n.localize_tree(w)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Show and i18n.get_language() == i18n.EN
                and isinstance(obj, QWidget) and obj.isWindow()):
            def apply_later(widget=obj):
                try:
                    i18n.localize_tree(widget)
                except Exception:
                    pass
            QTimer.singleShot(0, apply_later)
        return super().eventFilter(obj, event)

    def _toggle_advanced(self, on: bool):
        self.advanced.setVisible(on)

    def _set_mode(self, mode: int, initial: bool = False):
        self._clear_pending_random()
        self._reset_calibration()
        self.mode = 2 if mode == 2 else 1
        self.mode_group.button(self.mode).setChecked(True)
        self.viewer.set_mode(self.mode)
        self._refresh_mode_help()
        if not initial:
            self._set_status(
                "已切换到模式一：标注和计数保留，无需重跑 Cellpose；可用“全部设为已计数”统一状态。"
                if self.mode == 1 else
                "已切换到模式二：标注和计数保留，无需重跑 Cellpose；可用“全部设为未计数”统一状态。")
        self._update_counts()
        self._sync_random_controls()

    def _clear_calibration_display(self):
        self.viewer.clear_calibration_line()

    def _reset_calibration(self):
        self.calib_timer.stop()
        self._calibration_real_um = None
        self.viewer.clear_calibration_line()

    def start_calibration(self):
        if self.loaded is None:
            QMessageBox.information(self, "需要图像", "请先打开一张图像。")
            return
        self._clear_pending_random()
        self._reset_calibration()
        value, ok = QInputDialog.getDouble(
            self, "手动标定比例",
            "已知真实长度（µm）：", 20.0, 1e-6, 1e9, 4)
        if not ok:
            return
        self._calibration_real_um = float(value)
        self.viewer.start_calibration()
        self.viewer.setFocus()
        self._set_status(
            f"手动标定：已知长度 {value:g} µm。请在图像上点击两点；Esc 取消。")

    def _on_calibration_cancelled(self):
        if self._calibration_real_um is not None:
            self._calibration_real_um = None
            self._set_status("已取消手动标定。")

    def _on_calibration_finished(self, x1, y1, x2, y2):
        real_um = self._calibration_real_um
        self._calibration_real_um = None
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if real_um is None or (dx < 0.5 and dy < 0.5):
            self.viewer.clear_calibration_line()
            self._set_status("标定线太短，请重新标定。")
            return
        snapped = ""
        if dx >= dy:
            angle = math.degrees(math.atan2(dy, dx))
            if 0.5 < dy and angle <= 5.0:
                if QMessageBox.question(
                        self, "校正为水平线",
                        f"这条线与水平方向相差 {angle:.1f}°。\n"
                        "是否校正为水平线来计算比例？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes) == QMessageBox.Yes:
                    y2 = y1
                    snapped = "（已校正为水平线）"
        else:
            angle = math.degrees(math.atan2(dx, dy))
            if 0.5 < dx and angle <= 5.0:
                if QMessageBox.question(
                        self, "校正为垂直线",
                        f"这条线与垂直方向相差 {angle:.1f}°。\n"
                        "是否校正为垂直线来计算比例？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes) == QMessageBox.Yes:
                    x2 = x1
                    snapped = "（已校正为垂直线）"
        length_px = math.hypot(x2 - x1, y2 - y1)
        if length_px < 0.5:
            self.viewer.clear_calibration_line()
            self._set_status("标定线太短，请重新标定。")
            return
        ratio = real_um / length_px
        self.spin_pixel.setValue(ratio)
        self.viewer.set_calibration_line(
            (x1, y1), (x2, y2),
            f"{real_um:g} µm / {length_px:.1f} px = {ratio:.6g} µm/px")
        self.calib_timer.start(5000)
        self._set_status(
            f"比例已更新：{ratio:.6g} µm/px"
            f"（{real_um:g} µm ÷ {length_px:.2f} px）{snapped}")

    def _sync_random_controls(self):
        mode2 = self.mode == 2
        has_cells = bool(self.store and self.store.metas)
        if hasattr(self, "btn_mode_reset"):
            self.btn_mode_reset.setText(
                "全部设为已计数" if self.mode == 1 else "全部设为未计数")
            self.btn_mode_reset.setEnabled(has_cells)
        if hasattr(self, "act_mode_reset"):
            self.act_mode_reset.setText(
                "全部设为已计数（模式一）" if self.mode == 1
                else "全部设为未计数（模式二）")
            self.act_mode_reset.setEnabled(has_cells)
        if hasattr(self, "btn_random"):
            self.btn_random.setVisible(mode2)
            self.btn_random.setEnabled(mode2 and has_cells)
        if hasattr(self, "act_random"):
            self.act_random.setEnabled(mode2 and has_cells)

    def reset_counts_for_mode(self):
        self._clear_pending_random()
        if not self.store or not self.store.metas:
            QMessageBox.information(self, "没有细胞", "当前没有可操作的细胞。")
            return
        target = self.mode == 1
        if not target:
            answer = QMessageBox.question(
                self, "全部设为未计数",
                "将把所有细胞设为未计数（只改变计数状态，不删除标注），之后可继续逐个确认。\n\n"
                "此操作可以撤销。是否继续？")
            if answer != QMessageBox.Yes:
                return
        ids = list(self.store.metas.keys())
        changed = self.store.set_counted(ids, target)
        self.viewer.set_selection([])
        self.viewer.refresh()
        self._update_ui()
        state = "已计数" if target else "未计数"
        if changed:
            self._set_status(f"已将 {changed} 个细胞设为{state}。")
        else:
            self._set_status(f"所有细胞已经是{state}状态。")

    def random_select_cells(self):
        if self.mode != 2:
            QMessageBox.information(
                self, "随机选取", "随机选取功能仅在模式二（逐个确认）中可用。")
            return
        total = len(self.store)
        if total == 0:
            QMessageBox.information(self, "没有细胞", "请先运行 Cellpose 或手动绘制细胞。")
            return
        self._clear_pending_random()
        uncounted = [cid for cid, meta in self.store.metas.items() if not meta.counted]
        dlg = RandomSelectDialog(total, len(uncounted), self)
        if dlg.exec_() != QDialog.Accepted:
            return
        candidates = uncounted if dlg.only_from_uncounted() else list(self.store.metas)
        ids = self.store.spatially_uniform_sample(dlg.count(), candidates)
        if not ids:
            QMessageBox.information(self, "没有候选细胞", "当前没有可选取的细胞。")
            return
        self._begin_pending_random(ids)

    def _set_random_shortcuts(self, enabled: bool):
        for name in ("sc_confirm_return", "sc_confirm_enter", "sc_cancel_random"):
            sc = getattr(self, name, None)
            if sc is not None:
                sc.setEnabled(bool(enabled))

    def _begin_pending_random(self, ids: list[int]):
        self.pending_random_ids = [int(i) for i in ids]
        self.viewer.set_selection([])
        self.viewer.set_preview(self.pending_random_ids)
        self.lbl_random_confirm.setText(
            f"已随机选中 {len(self.pending_random_ids)} 个细胞（蓝色）。"
            "按 Enter 确认计数，按 Esc 取消。")
        self.lbl_random_confirm.show()
        self._set_random_shortcuts(True)
        self.viewer.setFocus()
        self._set_status("随机选取：按 Enter 确认计数，按 Esc 取消。")

    def _clear_pending_random(self) -> bool:
        had = self.pending_random_ids is not None
        self.pending_random_ids = None
        if hasattr(self, "lbl_random_confirm"):
            self.lbl_random_confirm.hide()
        self._set_random_shortcuts(False)
        if hasattr(self, "viewer"):
            self.viewer.clear_preview()
        return had

    def confirm_pending_random(self):
        if not self.pending_random_ids:
            return
        ids = list(self.pending_random_ids)
        self._clear_pending_random()
        self.store.set_counted(ids, True)
        self.viewer.refresh()
        self._update_ui()
        self._set_status(f"已确认计数 {len(ids)} 个随机选取的细胞。")

    def cancel_pending_random(self):
        if self.pending_random_ids is None:
            return
        self._clear_pending_random()
        self.viewer.refresh()
        self._update_ui()
        self._set_status("已取消随机计数。")

    def _set_status(self, text: str):
        self.lbl_status.setText(i18n.translate(text))

    # --------------------------------------------------------------- batch I/O
    def _capture_cellpose_settings(self) -> dict:
        source = self.combo_source.currentData() or ("auto", 0)
        source_kind, source_idx = source
        return {
            "model": self.combo_model.currentData() or "cyto3",
            "source": str(source_kind),
            "channel": int(source_idx) + 1,
            "diameter": "auto" if self.chk_auto_dia.isChecked()
            else str(self.spin_dia.value()),
            "flow": float(self.spin_flow.value()),
            "cellprob": float(self.spin_cellprob.value()),
            "min_size": int(self.spin_min.value()),
        }

    def _batch_args(self, item: BatchItem) -> list[str]:
        s = item.settings
        return [
            str(APP_ROOT / "cellpose_worker.py"),
            "--image", str(item.path),
            "--model", s["model"],
            "--source", s["source"],
            "--channel", str(s["channel"]),
            "--diameter", s["diameter"],
            "--flow", f"{s['flow']:.3f}",
            "--cellprob", f"{s['cellprob']:.3f}",
            "--min-size", str(s["min_size"]),
            "--output", str(item.masks_path),
            "--models-dir", str(MODELS_DIR),
        ]

    def choose_batch_files(self):
        filters = (i18n.translate("图像文件") + " (*" + " *".join(IMAGE_EXTENSIONS)
                   + ");;" + i18n.translate("所有文件") + " (*.*)")
        files, _ = QFileDialog.getOpenFileNames(
            self, i18n.translate("添加到批量处理"), str(Path.home()), filters)
        if files:
            self.add_batch_files(files)

    def add_batch_files(self, paths):
        valid = []
        for raw in paths:
            p = Path(raw)
            if p.is_dir():
                try:
                    valid.extend([c for c in p.iterdir()
                                  if c.is_file() and c.suffix.lower() in IMAGE_EXTENSIONS])
                except OSError:
                    continue
            elif p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                valid.append(p)
        valid = [p for p in valid if p.exists()]
        if not valid:
            return
        if self.batch_dir is None:
            self.batch_dir = TEMP_ROOT / f"batch_{time.strftime('%Y%m%d_%H%M%S')}"
        self.batch_dir.mkdir(parents=True, exist_ok=True)
        settings = self._capture_cellpose_settings()
        added = 0
        for path in valid:
            if any(item.path == path and item.status != "error"
                   for item in self.batch_items.values()):
                continue
            item_id = self.batch_next_id
            work = self.batch_dir / f"item_{item_id:03d}"
            work.mkdir(parents=True, exist_ok=True)
            item = BatchItem(
                id=item_id, path=path, settings=dict(settings), work_dir=work,
                masks_path=work / "masks.npy", state_path=work / "state.npz")
            self.batch_items[item_id] = item
            self.batch_order.append(item_id)
            self.batch_next_id += 1
            added += 1
        if added == 0:
            self._update_batch_status()
            return
        if self.loaded is None and self.batch_current_loaded_id is None:
            self.batch_autoload_first = True
        self._rebuild_batch_list()
        self._update_batch_status()
        self._start_next_batch()

    def _batch_item_label(self, item: BatchItem) -> tuple[str, QColor]:
        names = {
            "queued": "排队", "running": "处理中…", "ready": "待校正",
            "editing": "校正中", "edited": "已保存", "error": "失败",
        }
        colors = {
            "queued": QColor(theme.TEXT_DIM),
            "running": QColor(theme.CYAN),
            "ready": QColor(theme.YELLOW),
            "editing": QColor(theme.ACCENT),
            "edited": QColor(theme.ACCENT),
            "error": QColor(theme.DANGER),
        }
        text = f"{item.path.name}  ·  {names.get(item.status, item.status)}"
        if item.status in ("ready", "editing", "edited"):
            text += f"  ({item.counted}/{item.n_cells})"
        return text, colors.get(item.status, QColor(theme.TEXT_MUTED))

    def _rebuild_batch_list(self):
        if not hasattr(self, "batch_list"):
            return
        self.batch_list.blockSignals(True)
        self.batch_list.clear()
        for item_id in self.batch_order:
            item = self.batch_items.get(item_id)
            if item is None:
                continue
            text, color = self._batch_item_label(item)
            entry = QListWidgetItem(text)
            entry.setData(Qt.UserRole, item_id)
            entry.setToolTip(str(item.path))
            entry.setForeground(color)
            if item.status == "error":
                entry.setToolTip(f"{item.path}\n{item.error}")
            self.batch_list.addItem(entry)
            if self.batch_current_loaded_id == item_id:
                f = entry.font()
                f.setBold(True)
                entry.setFont(f)
                self.batch_list.setCurrentItem(entry)
        self.batch_list.blockSignals(False)

    def _update_batch_status(self):
        if not hasattr(self, "lbl_batch_status"):
            return
        total = len(self.batch_items)
        if total == 0:
            self.lbl_batch_status.setText("拖入图像或点击“添加文件”。")
            if hasattr(self, "btn_clear_batch"):
                self.btn_clear_batch.setEnabled(False)
            return
        running = sum(1 for i in self.batch_items.values() if i.status == "running")
        ready = sum(1 for i in self.batch_items.values()
                    if i.status in ("ready", "editing", "edited"))
        errors = sum(1 for i in self.batch_items.values() if i.status == "error")
        text = f"队列 {total} · 处理中 {running} · 待校正 {ready} · 失败 {errors}"
        if self.batch_stage and self.batch_processing_id is not None:
            item = self.batch_items.get(self.batch_processing_id)
            name = item.path.name if item else ""
            text += f"\n{name}：{self.batch_stage}"
        self.lbl_batch_status.setText(text)
        if hasattr(self, "btn_clear_batch"):
            self.btn_clear_batch.setEnabled(True)

    def _start_next_batch(self):
        if not self.batch_items or self.batch_proc is not None or self.cp_proc is not None:
            self._update_batch_status()
            return
        item = next((self.batch_items[i] for i in self.batch_order
                     if self.batch_items[i].status == "queued"), None)
        if item is None:
            self.batch_stage = ""
            self._update_batch_status()
            return
        item.status = "running"
        self.batch_processing_id = item.id
        self.batch_buf = ""
        self.batch_log = ""
        self.batch_done_payload = None
        self.batch_error = ""
        self.batch_stage = "启动…"
        self._rebuild_batch_list()
        self._update_batch_status()

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(str(APP_ROOT))
        proc.setProcessEnvironment(self._process_env())
        proc.readyReadStandardOutput.connect(self._batch_read)
        proc.finished.connect(self._batch_finished)
        proc.errorOccurred.connect(self._batch_proc_error)
        self.batch_proc = proc
        proc.start(sys.executable, self._batch_args(item))
        if not proc.waitForStarted(5000):
            self._batch_finished(-1, QProcess.CrashExit)

    def _batch_read(self):
        if self.batch_proc is None:
            return
        raw = bytes(self.batch_proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.batch_buf += raw
        while "\n" in self.batch_buf:
            line, self.batch_buf = self.batch_buf.split("\n", 1)
            self._handle_batch_line(line.rstrip("\r"))

    def _handle_batch_line(self, line: str):
        if not line.strip():
            return
        if line.lstrip().startswith("{"):
            try:
                ev = json.loads(line)
            except Exception:
                self.batch_log += line + "\n"
                return
            kind = ev.get("event")
            if kind == "stage":
                self.batch_stage = str(ev.get("message", ""))
                self._update_batch_status()
            elif kind == "done":
                self.batch_done_payload = ev
            elif kind == "error":
                self.batch_error = str(ev.get("message", "批量 Cellpose 失败"))
                self.batch_log += line + "\n"
        else:
            self.batch_log += line + "\n"

    def _batch_proc_error(self, err):
        if err == QProcess.FailedToStart:
            self.batch_error = "无法启动批量 Cellpose worker。"

    def _batch_finished(self, code, status):
        if self.batch_proc is None and self.batch_processing_id is None:
            return
        if self.batch_proc is not None:
            raw = bytes(self.batch_proc.readAllStandardOutput()).decode("utf-8", "replace")
            self.batch_buf += raw
            for line in self.batch_buf.splitlines():
                self._handle_batch_line(line)
        proc = self.batch_proc
        self.batch_proc = None
        item = self.batch_items.get(self.batch_processing_id) if self.batch_processing_id else None
        self.batch_processing_id = None
        if item is not None:
            if self.batch_done_payload is not None:
                item.status = "ready"
                item.n_cells = int(self.batch_done_payload.get("n_cells", 0))
                item.counted = 0
                mp = self.batch_done_payload.get("masks")
                if mp:
                    item.masks_path = Path(mp)
                item.error = ""
            else:
                item.status = "error"
                item.error = self.batch_error or (self.batch_log[-2000:] or "批量处理失败")
        self.batch_stage = ""
        self._rebuild_batch_list()
        self._update_batch_status()
        if (item is not None and item.status == "ready"
                and self.batch_autoload_first and self.loaded is None):
            self.batch_autoload_first = False
            self.load_batch_item(item)
            self._rebuild_batch_list()
            self._update_batch_status()
        self._start_next_batch()

    def _on_batch_item_clicked(self, entry: QListWidgetItem):
        if entry is None:
            return
        item_id = entry.data(Qt.UserRole)
        item = self.batch_items.get(int(item_id)) if item_id is not None else None
        if item is None:
            return
        if item.status in ("queued", "running"):
            self._set_status("该图像还在排队或处理中，请稍候。")
            return
        if item.status == "error":
            QMessageBox.critical(self, "批量处理失败", item.error or "未知错误")
            return
        self.load_batch_item(item)

    def load_batch_item(self, item: BatchItem):
        if item.status not in ("ready", "editing", "edited"):
            return
        if self.batch_current_loaded_id == item.id:
            return
        self._detach_current_batch()
        self.batch_autoload_first = False
        self.open_image(item.path)
        if self.loaded is None:
            return
        try:
            if item.state_path is not None and item.state_path.exists():
                data = np.load(item.state_path, allow_pickle=False)
                labels = np.asarray(data["labels"], np.int32)
                ids = np.asarray(data["ids"], np.int64)
                origins_arr = np.asarray(data["origins"])
                counted_arr = np.asarray(data["counted"], bool)
                next_id = int(data["next_id"])
                origins = {int(i): str(o) for i, o in zip(ids, origins_arr)}
                counted = {int(i) for i, c in zip(ids, counted_arr) if c}
                store = CellStore(labels.shape)
                store.load_session(labels, origins, counted, next_id)
                self.store = store
            elif item.masks_path is not None and item.masks_path.exists():
                masks = np.load(item.masks_path)
                self.store.set_from_mask(masks, count_all=(self.mode == 1))
            else:
                QMessageBox.critical(self, "没有结果", "该文件没有可用的自动标注结果。")
                return
            self.viewer.set_store(self.store)
            self.viewer.fit()
            item.status = "editing"
            item.n_cells = len(self.store)
            item.counted = len(self.store.counted_ids())
            self.batch_current_loaded_id = item.id
            self._update_ui()
            self._rebuild_batch_list()
            self._update_batch_status()
            self._set_status(f"已载入批量文件：{item.path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "载入批量结果失败", str(exc))

    def _save_current_batch_state(self):
        item_id = self.batch_current_loaded_id
        if item_id is None:
            return
        item = self.batch_items.get(item_id)
        if item is None or item.state_path is None:
            return
        try:
            ids = sorted(self.store.metas)
            origins = np.array([self.store.metas[i].origin for i in ids], dtype="U6")
            counted = np.array([self.store.metas[i].counted for i in ids], dtype=bool)
            item.state_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                item.state_path,
                labels=self.store.labels,
                ids=np.array(ids, np.int64),
                origins=origins,
                counted=counted,
                next_id=np.int64(self.store.next_id),
            )
            item.n_cells = len(self.store)
            item.counted = len(self.store.counted_ids())
        except Exception:
            pass

    def _detach_current_batch(self):
        if self.batch_current_loaded_id is None:
            return
        self._save_current_batch_state()
        item = self.batch_items.get(self.batch_current_loaded_id)
        if item is not None:
            item.status = "edited"
        self.batch_current_loaded_id = None
        self._rebuild_batch_list()
        self._update_batch_status()

    def clear_batch(self):
        if not self.batch_items:
            return
        if QMessageBox.question(
                self, "清空批量队列",
                "清空所有批量任务（正在处理的会停止；已保存的标注不会删除，"
                "但将不再出现在批量列表中）。是否继续？") != QMessageBox.Yes:
            return
        self._save_current_batch_state()
        if self.batch_proc is not None:
            proc = self.batch_proc
            self.batch_proc = None
            self.batch_processing_id = None
            try:
                proc.kill()
            except Exception:
                pass
        self.batch_items.clear()
        self.batch_order.clear()
        self.batch_current_loaded_id = None
        self.batch_autoload_first = False
        self.batch_stage = ""
        if hasattr(self, "batch_list"):
            self.batch_list.clear()
        self._update_batch_status()

    # -------------------------------------------------------------- image I/O
    def open_image_dialog(self):
        filters = (i18n.translate("图像文件") + " (*" + " *".join(IMAGE_EXTENSIONS)
                   + ");;" + i18n.translate("所有文件") + " (*.*)")
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.translate("打开图像"), str(Path.home()), filters)
        if path:
            self.open_image(Path(path))

    def open_image(self, path: Path):
        self._clear_pending_random()
        self._reset_calibration()
        if self.batch_current_loaded_id is not None:
            self._detach_current_batch()
        self.batch_autoload_first = False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            loaded = load_image(path)
        except Exception as exc:
            QMessageBox.critical(self, "无法打开图像", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        self.loaded = loaded
        self.store = CellStore((loaded.height, loaded.width))
        self.viewer.set_image(loaded.display_rgb)
        self.viewer.set_store(self.store)
        self.viewer.fit()
        self.viewer.setFocus()

        self.lbl_file.setText(loaded.path.name)
        self.lbl_file.setToolTip(str(loaded.path))
        self.lbl_image_info.setText(loaded.info_text)
        if loaded.warning:
            self.lbl_warning.setText(loaded.warning)
            self.lbl_warning.show()
        else:
            self.lbl_warning.hide()
        self.out_dir = loaded.path.parent / "SimpleCellSegmentation_results"
        self._update_outdir_label()
        self._populate_display_combo(loaded)
        self._populate_source_combo(loaded)
        self.last_results = None
        self.btn_results.hide()
        self._set_status(f"已载入 {loaded.path.name}。可以运行 Cellpose 自动标注。")
        self._update_ui()

    def _populate_display_combo(self, loaded: LoadedImage):
        self.combo_display.blockSignals(True)
        self.combo_display.clear()
        self.combo_display.addItem("复合显示", "composite")
        if loaded.n_channels == 1:
            self.combo_display.addItem("灰度", ("channel", 0))
        else:
            for i in range(loaded.n_channels):
                self.combo_display.addItem(
                    f"{loaded.channel_display_name(i)} · 灰度", ("channel", i))
        self.combo_display.blockSignals(False)

    def _populate_source_combo(self, loaded: LoadedImage):
        self.combo_source.blockSignals(True)
        self.combo_source.clear()
        auto_i = loaded.auto_seg_channel()
        auto_name = loaded.channel_display_name(auto_i)
        self.combo_source.addItem(f"自动 · {auto_name}", ("auto", 0))
        self.combo_source.addItem("复合图像", ("composite", 0))
        for i in range(loaded.n_channels):
            self.combo_source.addItem(
                f"{loaded.channel_display_name(i)} · 单通道", ("channel", i))
        self.combo_source.blockSignals(False)

    def _on_display_changed(self, _idx):
        if self.loaded is None:
            return
        data = self.combo_display.currentData()
        if data == "composite":
            rgb = self.loaded.display_rgb
        else:
            kind, i = data
            ch = self.loaded.display_channels[i]
            rgb = np.repeat(ch[..., None], 3, axis=2)
        self.viewer.set_image(rgb, keep_view=True)
        self.viewer.refresh()

    # ----------------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            p = Path(url.toLocalFile())
            if p.is_dir():
                try:
                    files.extend([c for c in p.iterdir()
                                  if c.is_file() and c.suffix.lower() in IMAGE_EXTENSIONS])
                except OSError:
                    pass
            elif p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                files.append(p)
        if not files:
            return
        event.acceptProposedAction()
        if len(files) == 1:
            self.open_image(files[0])
        else:
            self.add_batch_files(files)

    # --------------------------------------------------------------- cellpose
    def _process_env(self) -> QProcessEnvironment:
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        return env

    def run_cellpose(self):
        self._clear_pending_random()
        self._reset_calibration()
        if self.batch_proc is not None:
            QMessageBox.information(
                self, "批量处理中",
                "批量 Cellpose 正在后台运行。请等待完成，或在批量列表清空任务后再手动运行。")
            return
        if self.loaded is None:
            QMessageBox.information(self, "需要图像", "请先打开一张图像。")
            return
        if self.cp_proc is not None:
            return
        source_kind, source_idx = self.combo_source.currentData()
        model = self.combo_model.currentData()
        out_dir = Path(tempfile.mkdtemp(prefix="simplecs_cp_", dir=str(TEMP_ROOT)))
        out_npy = out_dir / "masks.npy"
        diameter = "auto" if self.chk_auto_dia.isChecked() else str(self.spin_dia.value())
        args = [
            str(APP_ROOT / "cellpose_worker.py"),
            "--image", str(self.loaded.path),
            "--model", model,
            "--source", source_kind,
            "--channel", str(int(source_idx) + 1),
            "--diameter", diameter,
            "--flow", f"{self.spin_flow.value():.3f}",
            "--cellprob", f"{self.spin_cellprob.value():.3f}",
            "--min-size", str(self.spin_min.value()),
            "--output", str(out_npy),
            "--models-dir", str(MODELS_DIR),
        ]
        self.cp_buf = ""
        self.cp_log = ""
        self.cp_done_payload = None
        self.cp_error = ""
        self.cp_cancelled = False

        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(str(APP_ROOT))
        proc.setProcessEnvironment(self._process_env())
        proc.readyReadStandardOutput.connect(self._cp_read)
        proc.finished.connect(self._cp_finished)
        proc.errorOccurred.connect(self._cp_proc_error)
        self.cp_proc = proc

        self.progress_cp.setRange(0, 0)
        self.progress_cp.show()
        self.btn_cancel_cp.show()
        self.btn_run_cp.setEnabled(False)
        self.btn_measure.setEnabled(False)
        self.lbl_cp_status.setText("正在启动 Cellpose worker…")
        self._set_status("Cellpose 正在运行，请稍候…")
        proc.start(sys.executable, args)
        if not proc.waitForStarted(5000):
            self._set_status("无法启动 Cellpose worker。")
            self._cp_finished(-1, QProcess.CrashExit)

    def _cp_read(self):
        if self.cp_proc is None:
            return
        raw = bytes(self.cp_proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.cp_buf += raw
        while "\n" in self.cp_buf:
            line, self.cp_buf = self.cp_buf.split("\n", 1)
            self._handle_cp_line(line.rstrip("\r"))

    def _handle_cp_line(self, line: str):
        if not line.strip():
            return
        if line.lstrip().startswith("{"):
            try:
                ev = json.loads(line)
            except Exception:
                self.cp_log += line + "\n"
                return
            kind = ev.get("event")
            if kind == "stage":
                msg = str(ev.get("message", ""))
                self.lbl_cp_status.setText(msg)
                self._set_status(msg)
            elif kind == "done":
                self.cp_done_payload = ev
            elif kind == "model_missing":
                self.cp_error = "模型文件缺失，请点击“检查 / 下载模型”。"
            elif kind == "error":
                self.cp_error = str(ev.get("message", "Cellpose 运行失败"))
                self.cp_log += line + "\n"
        else:
            self.cp_log += line + "\n"
            low = line.lower()
            if "error" in low or "traceback" in low:
                self._set_status(line[:160])

    def _cp_proc_error(self, err):
        if err == QProcess.FailedToStart:
            self.cp_error = "无法启动 Python worker，请检查 Python 环境。"

    def _cp_finished(self, code, status):
        if self.cp_proc is not None:
            raw = bytes(self.cp_proc.readAllStandardOutput()).decode("utf-8", "replace")
            self.cp_buf += raw
            for line in self.cp_buf.splitlines():
                self._handle_cp_line(line)
        self.cp_proc = None
        self.progress_cp.hide()
        self.btn_cancel_cp.hide()
        self.btn_run_cp.setEnabled(True)
        self._update_ui()

        if self.cp_cancelled:
            self.lbl_cp_status.setText("已取消 Cellpose。")
            self._set_status("已取消 Cellpose。")
        elif self.cp_done_payload is not None:
            payload = self.cp_done_payload
            try:
                masks = np.load(payload["masks"])
                if masks.shape != (self.loaded.height, self.loaded.width):
                    raise RuntimeError(
                        f"掩膜尺寸 {masks.shape} 与图像 "
                        f"({self.loaded.height}, {self.loaded.width}) 不一致")
                n = self.store.set_from_mask(masks, count_all=(self.mode == 1))
                self.viewer.set_store(self.store)
                self.viewer.refresh()
                self._update_ui()
                elapsed = payload.get("elapsed", "?")
                dia = payload.get("diameter", "")
                self.lbl_cp_status.setText(
                    f"完成：{n} 个细胞 · {elapsed}s · 直径 {dia}。")
                self._set_status(
                    f"Cellpose 完成：{n} 个细胞。"
                    + ("已全部计数。" if self.mode == 1 else "请逐个点击确认。"))
            except Exception as exc:
                self._cp_error_dialog(f"加载 Cellpose 结果失败：{exc}")
        else:
            msg = self.cp_error or "Cellpose 未返回结果。"
            self._cp_error_dialog(msg)
        self._start_next_batch()

    def _cp_error_dialog(self, msg: str):
        self.lbl_cp_status.setText(msg)
        self._set_status(msg)
        detail = (self.cp_log or "")[-4000:]
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("Cellpose 运行失败")
        box.setText(msg)
        if detail:
            box.setDetailedText(detail)
        box.exec_()

    def cancel_cellpose(self):
        if self.cp_proc is not None:
            self.cp_cancelled = True
            self.cp_proc.kill()
            self._set_status("正在取消 Cellpose…")

    def check_model(self):
        if self.dl_proc is not None:
            QMessageBox.information(self, "请稍候", "模型正在下载中。")
            return
        model = self.combo_model.currentData()
        files = []
        missing = []
        for filename, minimum, _urls in MODEL_FILES[model]:
            path = MODELS_DIR / filename
            files.append(path)
            if not path.exists() or path.stat().st_size < minimum:
                missing.append(path)
        if not missing:
            info = "\n".join(
                f"{p.name}: {p.stat().st_size / (1024 * 1024):.1f} MB" for p in files)
            QMessageBox.information(
                self, "模型已就绪",
                f"{model} 模型已存在：\n\n{info}\n\n目录：{MODELS_DIR}")
            return
        size_hint = ("约 1.2 GB" if model in ("cpsam_v2", "cpsam") else "约 26 MB")
        text = (
            "缺少以下模型文件：\n\n" + "\n".join(str(p) for p in missing)
            + f"\n\n{model} 下载大小{size_hint}。"
            + "\n推荐优先使用 cyto3（约 26 MB，速度快）。"
            + "\n\n是否现在下载当前模型？"
        )
        if QMessageBox.question(self, "下载模型", text) != QMessageBox.Yes:
            return
        self._start_download(model)

    def _start_download(self, model: str):
        self.dl_buf = ""
        self.dl_ok = False
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(str(APP_ROOT))
        proc.setProcessEnvironment(self._process_env())
        proc.readyReadStandardOutput.connect(self._dl_read)
        proc.finished.connect(self._dl_finished)
        self.dl_proc = proc
        self.progress_cp.setRange(0, 100)
        self.progress_cp.setValue(0)
        self.progress_cp.show()
        self.btn_run_cp.setEnabled(False)
        self.btn_model.setEnabled(False)
        self.lbl_cp_status.setText("准备下载模型…")
        self._set_status("正在下载模型…")
        args = [
            str(APP_ROOT / "download_model.py"),
            "--model", model, "--dest", str(MODELS_DIR),
        ]
        proc.start(sys.executable, args)

    def _dl_read(self):
        if self.dl_proc is None:
            return
        raw = bytes(self.dl_proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.dl_buf += raw
        while "\n" in self.dl_buf:
            line, self.dl_buf = self.dl_buf.split("\n", 1)
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("event") == "progress":
                done = int(ev.get("done", 0))
                total = int(ev.get("total", 0))
                if total > 0:
                    self.progress_cp.setRange(0, 100)
                    self.progress_cp.setValue(max(0, min(100, int(done * 100 / total))))
                    self.lbl_cp_status.setText(
                        f"下载 {ev.get('label', '模型')}… "
                        f"{done / 1e6:.0f} / {total / 1e6:.0f} MB")
                else:
                    self.lbl_cp_status.setText(
                        f"下载 {ev.get('label', '模型')}… {done / 1e6:.0f} MB")
            elif ev.get("event") == "done":
                self.dl_ok = True
            elif ev.get("event") == "error":
                self.lbl_cp_status.setText(str(ev.get("message", "下载失败")))

    def _dl_finished(self, code, status):
        self.dl_proc = None
        self.progress_cp.hide()
        self.btn_run_cp.setEnabled(True)
        self.btn_model.setEnabled(True)
        if self.dl_ok:
            self.lbl_cp_status.setText("模型下载完成，可以运行 Cellpose。")
            self._set_status("模型下载完成。")
        else:
            msg = self.lbl_cp_status.text() or "模型下载失败。"
            QMessageBox.warning(self, "模型下载失败", msg)

    # ----------------------------------------------------------------- ImageJ
    def choose_output_dir(self):
        start = str(self.out_dir or (self.loaded.path.parent if self.loaded else Path.home()))
        d = QFileDialog.getExistingDirectory(
            self, i18n.translate("选择结果输出文件夹"), start)
        if d:
            self.out_dir = Path(d)
            self._update_outdir_label()

    def _update_outdir_label(self):
        if self.out_dir is None:
            self.lbl_outdir.setText("载入图像后自动设置")
        else:
            self.lbl_outdir.setText(str(self.out_dir))
            self.lbl_outdir.setToolTip(str(self.out_dir))

    def run_imagej(self):
        self._clear_pending_random()
        self._reset_calibration()
        if self.loaded is None:
            QMessageBox.information(self, "需要图像", "请先打开图像并完成标注。")
            return
        if self.ij_proc is not None:
            return
        counted = self.store.counted_ids()
        if not counted:
            QMessageBox.information(
                self, "没有已计数细胞",
                "请先在模式一中运行 Cellpose，或在模式二中点击确认细胞。")
            return
        java, jar = find_imagej(APP_ROOT)
        if java is None or jar is None:
            QMessageBox.critical(
                self, "找不到 ImageJ",
                "未找到 ImageJ 的 java.exe / ij.jar。\n\n"
                "请把 ImageJ 1.54g 放到程序目录或上一级目录的 ImageJ 文件夹，"
                "或设置环境变量 IMAGEJ_HOME。")
            return

        try:
            label_mask, ids = self.store.export_label_mask()
            if self.out_dir is None:
                self.out_dir = self.loaded.path.parent / "SimpleCellSegmentation_results"
            self.out_dir.mkdir(parents=True, exist_ok=True)
            stem = self.loaded.path.stem
            setup = prepare_measurement(
                label_mask, self.out_dir, stem,
                self.spin_pixel.value(), TEMP_ROOT)
        except Exception as exc:
            QMessageBox.critical(self, "准备测量失败", str(exc))
            return

        self.ij_setup = setup
        self.ij_snapshot_mask = label_mask
        self.ij_snapshot_display = self.loaded.display_rgb.copy()
        self.ij_rows = []
        self.ij_log = ""
        self.ij_buf = ""
        self.ij_version = ""
        self.ij_cancelled = False
        self.ij_done = False

        args = [
            "-Xmx4096m",
            "-Djava.awt.headless=true",
            "-Dfile.encoding=UTF-8",
            "-jar", str(jar),
            "-batch", str(setup.ijm_path),
        ]
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.setWorkingDirectory(str(APP_ROOT))
        proc.readyReadStandardOutput.connect(self._ij_read)
        proc.finished.connect(self._ij_finished)
        self.ij_proc = proc

        self.progress_ij.setRange(0, 0)
        self.progress_ij.show()
        self.btn_cancel_ij.show()
        self.btn_measure.setEnabled(False)
        self.lbl_ij_status.setText(
            f"ImageJ 正在测量 {len(ids)} 个细胞…（headless）")
        self._set_status("ImageJ 正在计算每个细胞的面积…")
        proc.start(str(java), args)
        if not proc.waitForStarted(8000):
            self._set_status("无法启动 ImageJ。")
            self._ij_finished(-1, QProcess.CrashExit)

    def export_annotated_image(self):
        self._clear_pending_random()
        if self.loaded is None:
            QMessageBox.information(
                self, i18n.translate("需要图像"), i18n.translate("请先打开一张图像。"))
            return
        numbering = self.store.numbering()
        if not numbering:
            QMessageBox.information(
                self, i18n.translate("没有已计数细胞"),
                i18n.translate("请先在模式一中运行 Cellpose，或在模式二中点击确认细胞。"))
            return
        out_dir = self.out_dir or (self.loaded.path.parent / "SimpleCellSegmentation_results")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        default = out_dir / f"{self.loaded.path.stem}_annotated.png"
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.translate("导出标注图像"), str(default),
            i18n.translate("PNG 图像 (*.png)"))
        if not path:
            return
        path = Path(path)
        if path.suffix.lower() != ".png":
            path = path.with_suffix(".png")
        mask = np.zeros(self.store.labels.shape, dtype=np.uint16)
        for num, cid in enumerate(numbering, start=1):
            mask[self.store.labels == cid] = num
        try:
            edge_color = tuple(self.style.counted_edge.getRgb()[:3])
            write_annotation_image(
                self.loaded.display_rgb, mask, {}, path,
                color=edge_color, edge_width=self.style.edge_width)
            label_path = path.parent / f"{self.loaded.path.stem}_labels.tif"
            write_label_image(mask, label_path)
        except Exception as exc:
            QMessageBox.critical(
                self, i18n.translate("导出标注图像失败"), str(exc))
            return
        self._set_status(f"已导出标注图像：{path}")
        self.lbl_ij_status.setText(
            f"已导出标注图像：{path.name} · 标签文件：{label_path.name}")

    def _ij_read(self):
        if self.ij_proc is None:
            return
        raw = bytes(self.ij_proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.ij_buf += raw
        while "\n" in self.ij_buf:
            line, self.ij_buf = self.ij_buf.split("\n", 1)
            self._handle_ij_line(line.strip())

    def _handle_ij_line(self, line: str):
        if not line:
            return
        if line.startswith("CELL,"):
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    num = int(parts[1])
                    area = float(parts[2])
                    self.ij_rows.append((num, area))
                except Exception:
                    self.ij_log += line + "\n"
        elif line.startswith("IJ_DONE"):
            self.ij_done = True
        elif line.startswith("IJ_VERSION"):
            self.ij_version = line.replace("IJ_VERSION", "", 1).strip()
        else:
            self.ij_log += line + "\n"

    def _ij_finished(self, code, status):
        if self.ij_proc is not None:
            raw = bytes(self.ij_proc.readAllStandardOutput()).decode("utf-8", "replace")
            self.ij_buf += raw
            for line in self.ij_buf.splitlines():
                self._handle_ij_line(line.strip())
        self.ij_proc = None
        self.progress_ij.hide()
        self.btn_cancel_ij.hide()
        self.btn_measure.setEnabled(True)
        setup = self.ij_setup

        if self.ij_cancelled:
            self.lbl_ij_status.setText("已取消 ImageJ 测量。")
            self._set_status("已取消 ImageJ 测量。")
            return
        if setup is None:
            return
        if not self.ij_done or not self.ij_rows:
            msg = "ImageJ 没有返回测量结果。"
            self.lbl_ij_status.setText(msg)
            self._set_status(msg)
            detail = (self.ij_log or "")[-3000:]
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("ImageJ 测量失败")
            box.setText(msg)
            if detail:
                box.setDetailedText(detail)
            box.exec_()
            return

        rows = {int(n): float(a) for n, a in self.ij_rows}
        ordered = [(i, rows.get(i, 0.0)) for i in range(1, setup.n + 1)]
        zero = sum(1 for _, a in ordered if a <= 0)
        try:
            csv_path = setup.output_dir / f"{setup.stem}_cell_areas.csv"
            write_area_csv(ordered, csv_path, setup.pixel_size, self.ij_version)
        except Exception as exc:
            QMessageBox.critical(self, "保存结果失败", str(exc))
            return

        self.last_results = (csv_path, setup.output_dir)
        self.btn_results.show()
        unit = "µm²" if setup.pixel_size > 0 else "px²"
        self.lbl_ij_status.setText(
            f"完成：{setup.n} 个细胞 · {unit}"
            + (f" · {zero} 个面积为 0" if zero else ""))
        self._set_status(f"ImageJ 测量完成，已导出：{csv_path}")
        try:
            shutil.rmtree(setup.temp_dir, ignore_errors=True)
        except Exception:
            pass
        dialog = ResultsDialog(ordered, csv_path, setup.output_dir, unit, self)
        dialog.exec_()

    def cancel_imagej(self):
        if self.ij_proc is not None:
            self.ij_cancelled = True
            self.ij_proc.kill()
            self._set_status("正在取消 ImageJ 测量…")

    def open_last_results(self):
        if self.last_results:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_results[1])))

    # ------------------------------------------------------------------- table
    def _on_edit(self, message: str):
        self._clear_pending_random()
        if message:
            self._set_status(message)
        self._update_ui()

    def _update_ui(self):
        store = self.store
        counted_ids = store.counted_ids() if store else []
        total = len(store) if store else 0
        counted = len(counted_ids)
        manual = sum(1 for m in store.metas.values() if m.origin == "manual") if store else 0
        uncounted = total - counted
        self.lbl_big.setText(str(counted))
        if total == 0:
            self.lbl_summary.setText("尚未运行 Cellpose" if self.loaded is None else "暂无标注")
        else:
            self.lbl_summary.setText(
                f"自动检出 {total - manual} · 手动 {manual}\n"
                f"未计数 {uncounted} · 共 {total}")
        self.viewer.show_labels = self.btn_labels.isChecked()
        self._sync_table()
        self._update_counts()
        self._sync_random_controls()

        self.act_undo.setEnabled(store.can_undo)
        self.act_redo.setEnabled(store.can_redo)
        self.btn_undo.setEnabled(store.can_undo)
        self.btn_redo.setEnabled(store.can_redo)
        self.act_delete.setEnabled(bool(self.viewer.selected))
        self.act_save.setEnabled(self.loaded is not None)
        can_measure = self.loaded is not None and counted > 0
        self.act_measure.setEnabled(can_measure)
        self.btn_measure.setEnabled(can_measure and self.ij_proc is None)
        self.act_export_image.setEnabled(can_measure)
        self.btn_export_image.setEnabled(can_measure)
        self.btn_results.setVisible(self.last_results is not None)

    def _update_counts(self):
        if self.store is None:
            return
        total = len(self.store)
        counted = len(self.store.counted_ids())
        self.lbl_counts.setText(f"共 {total} · 计数 {counted}")
        self.lbl_zoom.setText(self.lbl_zoom.text())

    def _sync_table(self):
        if not hasattr(self, "table"):
            return
        numbers = self.store.numbering() if self.store else []
        scroll = self.table.verticalScrollBar().value()
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(len(numbers))
        for row, cid in enumerate(numbers):
            num = row + 1
            st = self.store.stats.get(cid)
            area = st.area if st else 0
            origin = "手动" if self.store.metas[cid].origin == "manual" else "自动"
            it_num = QTableWidgetItem(str(num))
            it_num.setTextAlignment(Qt.AlignCenter)
            it_num.setData(Qt.UserRole, cid)
            it_area = QTableWidgetItem(str(area))
            it_area.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_origin = QTableWidgetItem(origin)
            it_origin.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, it_num)
            self.table.setItem(row, 1, it_area)
            self.table.setItem(row, 2, it_origin)
        self.table.blockSignals(False)
        self.table.verticalScrollBar().setValue(scroll)
        self.lbl_table_hint.setText(
            "双击一行可定位到对应细胞。" if numbers else
            "运行 Cellpose 或手动绘制后，已计数细胞会显示在这里。")
        self._sync_table_selection()

    def _sync_table_selection(self):
        if not hasattr(self, "table"):
            return
        self.table.blockSignals(True)
        self.table.clearSelection()
        selected = self.viewer.selected if self.viewer else set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and int(item.data(Qt.UserRole)) in selected:
                self.table.selectRow(row)
        self.table.blockSignals(False)

    def _on_selection(self, ids: list):
        self.act_delete.setEnabled(bool(ids))
        self._sync_table_selection()

    def _on_table_click(self, row: int, _col: int):
        item = self.table.item(row, 0)
        if item is None:
            return
        cid = int(item.data(Qt.UserRole))
        self.viewer.set_selection([cid])

    def _on_table_double(self, row: int, _col: int):
        item = self.table.item(row, 0)
        if item is None:
            return
        cid = int(item.data(Qt.UserRole))
        self.viewer.zoom_to_cell(cid)

    # ------------------------------------------------------------------ edits
    def undo(self):
        self._clear_pending_random()
        if self.store.undo():
            self.viewer.refresh()
            self._update_ui()
            self._set_status("已撤销。")

    def redo(self):
        self._clear_pending_random()
        if self.store.redo():
            self.viewer.refresh()
            self._update_ui()
            self._set_status("已重做。")

    def delete_selected(self):
        self._clear_pending_random()
        if self.viewer.selected:
            n = self.store.delete_cells(self.viewer.selected)
            self.viewer.set_selection([])
            self.viewer.refresh()
            self._update_ui()
            self._set_status(f"已删除 {n} 个细胞。")

    def clear_all(self):
        self._clear_pending_random()
        if not self.store.has_cells:
            return
        if QMessageBox.question(
                self, "清除全部标注",
                "确定删除全部细胞标注吗？此操作可以撤销。") != QMessageBox.Yes:
            return
        self.store.clear_cells()
        self.viewer.set_selection([])
        self.viewer.refresh()
        self._update_ui()
        self._set_status("已清除全部标注。")

    # ------------------------------------------------------------- save/load
    def save_session(self):
        if self.loaded is None or not self.store.has_cells:
            QMessageBox.information(self, "没有可保存的标注", "当前没有细胞标注。")
            return
        default = str(self.loaded.path.with_suffix(".simplecellsegmentation.npz"))
        path, _ = QFileDialog.getSaveFileName(
            self, i18n.translate("保存标注"), default,
            i18n.translate("SimpleCellSegmentation 标注 (*.npz)"))
        if not path:
            return
        ids = sorted(self.store.metas)
        origins = np.array([self.store.metas[i].origin for i in ids], dtype="U6")
        counted = np.array([self.store.metas[i].counted for i in ids], dtype=bool)
        try:
            np.savez(
                path,
                labels=self.store.labels,
                ids=np.array(ids, np.int64),
                origins=origins,
                counted=counted,
                next_id=np.int64(self.store.next_id),
                image_path=np.array(str(self.loaded.path)),
                mode=np.int64(self.mode),
                pixel_size=np.float64(self.spin_pixel.value()),
            )
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self._set_status(f"标注已保存：{path}")

    def load_session(self):
        self._clear_pending_random()
        path, _ = QFileDialog.getOpenFileName(
            self, i18n.translate("载入标注"), str(Path.home()),
            i18n.translate("SimpleCellSegmentation 标注 (*.npz)"))
        if not path:
            return
        try:
            data = np.load(path, allow_pickle=False)
            labels = np.asarray(data["labels"], np.int32)
            ids = np.asarray(data["ids"], np.int64)
            origins_arr = np.asarray(data["origins"])
            counted_arr = np.asarray(data["counted"], bool)
            next_id = int(data["next_id"])
            image_path = Path(str(data["image_path"]))
            mode = int(data["mode"]) if "mode" in data else self.mode
            pixel = float(data["pixel_size"]) if "pixel_size" in data else 0.0
        except Exception as exc:
            QMessageBox.critical(self, "载入失败", str(exc))
            return

        if (self.loaded is None or self.loaded.path != image_path
                or (labels.shape[0], labels.shape[1]) != (self.loaded.height, self.loaded.width)):
            if not image_path.exists():
                QMessageBox.critical(
                    self, "找不到原图",
                    f"标注对应的原图不存在：\n{image_path}")
                return
            self.open_image(image_path)
            if self.loaded is None:
                return

        origins = {int(i): str(o) for i, o in zip(ids, origins_arr)}
        counted = {int(i) for i, c in zip(ids, counted_arr) if c}
        self.store = CellStore(labels.shape)
        self.store.load_session(labels, origins, counted, next_id)
        self.viewer.set_store(self.store)
        self.viewer.set_image(self.loaded.display_rgb)
        self.viewer.fit()
        self._set_mode(mode, initial=True)
        self.spin_pixel.setValue(pixel)
        self._update_ui()
        self._set_status(f"已载入标注：{path}")

    # ----------------------------------------------------------------- dialogs
    def show_shortcuts(self):
        if i18n.get_language() == i18n.EN:
            text = (
                "<b>Mouse</b><br>"
                "Left drag: draw / box-select according to the current mode<br>"
                "Left click: select / count<br>"
                "Alt + click / drag: delete cells<br>"
                "Ctrl + click / drag: uncount or restore (drag in Mode 2)<br>"
                "Shift + left drag: draw a new cell in Mode 2<br>"
                "Wheel: zoom around the cursor<br>"
                "Middle / right / Space + left drag: pan<br><br>"
                "<b>Keyboard</b><br>"
                "1 / 2: switch Mode 1 / Mode 2<br>"
                "Ctrl+Z / Ctrl+Y: undo / redo<br>"
                "Delete: delete selected cells<br>"
                "F: fit window　+ / −: zoom　Esc: cancel current action<br>"
                "Ctrl+R: run Cellpose　Ctrl+E: ImageJ measurement<br>"
                "Ctrl+O: open image　Ctrl+S: save labels"
            )
        else:
            text = (
                "<b>鼠标</b><br>"
                "左键拖动：根据当前模式绘制 / 框选<br>"
                "左键点击：选中 / 计数<br>"
                "Alt + 点击 / 拖动：删除细胞<br>"
                "Ctrl + 点击 / 拖动：取消或恢复计数（模式二拖动）<br>"
                "Shift + 左键拖动：模式二下绘制新细胞<br>"
                "滚轮：以光标为中心缩放<br>"
                "中键 / 右键 / 空格 + 左键拖动：平移<br><br>"
                "<b>键盘</b><br>"
                "1 / 2：切换模式一 / 模式二<br>"
                "Ctrl+Z / Ctrl+Y：撤销 / 重做<br>"
                "Delete：删除选中的细胞<br>"
                "F：适应窗口　+ / −：缩放　Esc：取消当前操作<br>"
                "Ctrl+R：运行 Cellpose　Ctrl+E：ImageJ 测量<br>"
                "Ctrl+O：打开图像　Ctrl+S：保存标注"
            )
        QMessageBox.information(
            self, i18n.translate("操作说明"), text)

    def show_about(self):
        if i18n.get_language() == i18n.EN:
            QMessageBox.about(
                self, "About SimpleCellSegmentation",
                "<b>SimpleCellSegmentation 1.1 (open source)</b><br><br>"
                "A convenience GUI for cell segmentation, manual correction and "
                "area measurement.<br><br>"
                "Segmentation is powered by Cellpose; area measurement is "
                "powered by ImageJ.<br><br>"
                "Cellpose model weights follow their original license (CC-BY-NC).<br>"
                "ImageJ 1.x is developed by NIH; PyQt5 follows GPL.")
            return
        QMessageBox.about(
            self, "关于 SimpleCellSegmentation",
            "<b>SimpleCellSegmentation 1.1（开源版）</b><br><br>"
            "一个更方便的操作工具 GUI：细胞分割、人工校正和面积测量。<br><br>"
            "识别工具来自 Cellpose；计算工具来自 ImageJ。<br><br>"
            "Cellpose 模型权重遵循其原始许可（CC-BY-NC）。<br>"
            "ImageJ 1.x 由 NIH 开发；PyQt5 遵循 GPL。")

    # ------------------------------------------------------------------ close
    def closeEvent(self, event):
        self.lang_timer.stop()
        try:
            QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        try:
            self._save_current_batch_state()
        except Exception:
            pass
        try:
            self.style.save()
        except Exception:
            pass
        if self.batch_proc is not None:
            try:
                self.batch_proc.kill()
                self.batch_proc.waitForFinished(1500)
            except Exception:
                pass
        if self.style_dialog is not None:
            try:
                self.style_dialog.close()
            except Exception:
                pass
        for proc in (self.cp_proc, self.ij_proc, self.dl_proc):
            if proc is not None:
                proc.kill()
                proc.waitForFinished(1500)
        super().closeEvent(event)
