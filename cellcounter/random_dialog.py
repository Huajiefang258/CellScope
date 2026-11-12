"""Dialog for spatially spread random cell sampling."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QSpinBox,
    QVBoxLayout, QWidget,
)

from . import theme


class RandomSelectDialog(QDialog):
    def __init__(self, total_count: int, uncounted_count: int, parent=None):
        super().__init__(parent)
        self.total_count = int(total_count)
        self.uncounted_count = int(uncounted_count)
        self.setWindowTitle("随机选取细胞")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setStyleSheet(theme.STYLESHEET)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(10)

        title = QLabel("随机选取细胞")
        title.setObjectName("appTitle")
        root.addWidget(title)
        sub = QLabel(
            "使用加权最远点采样：随机选取，同时让细胞在空间上尽量分散。"
            "选取后先显示为蓝色，按 Enter 确认计数，Esc 取消。")
        sub.setObjectName("hint")
        sub.setWordWrap(True)
        root.addWidget(sub)

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 6, 0, 0)
        h.setSpacing(10)
        lab = QLabel("选取数量")
        lab.setObjectName("hint")
        self.spin = QSpinBox()
        self.spin.setRange(1, max(1, self.total_count))
        self.spin.setValue(min(20, max(1, self.total_count)))
        self.spin.setSuffix(" 个")
        h.addWidget(lab)
        h.addWidget(self.spin, 1)
        root.addWidget(row)

        self.only_uncounted = QCheckBox("只从未计数细胞中选取")
        self.only_uncounted.setChecked(self.uncounted_count > 0)
        self.only_uncounted.setEnabled(self.uncounted_count > 0)
        self.only_uncounted.toggled.connect(self._refresh_max)
        root.addWidget(self.only_uncounted)

        self.info = QLabel("")
        self.info.setObjectName("dim")
        self.info.setWordWrap(True)
        root.addWidget(self.info)

        note = QLabel("数量等于候选数时会全选；每次运行结果不同。确认计数前不会改变现有计数。")
        note.setObjectName("dim")
        note.setWordWrap(True)
        root.addWidget(note)

        root.addStretch(1)
        buttons = QDialogButtonBox()
        self.btn_ok = buttons.addButton("随机选取", QDialogButtonBox.AcceptRole)
        self.btn_cancel = buttons.addButton("取消", QDialogButtonBox.RejectRole)
        self.btn_ok.setObjectName("primary")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_max()

    def _available(self) -> int:
        if self.only_uncounted.isChecked():
            return self.uncounted_count
        return self.total_count

    def _refresh_max(self):
        available = self._available()
        if available <= 0:
            self.spin.setRange(0, 0)
            self.spin.setEnabled(False)
            self.btn_ok.setEnabled(False)
            self.info.setText(f"候选细胞：0 个（总细胞 {self.total_count}，未计数 {self.uncounted_count}）")
            return
        self.spin.setEnabled(True)
        self.btn_ok.setEnabled(True)
        current = self.spin.value()
        self.spin.setRange(1, available)
        if current < 1:
            current = min(20, available)
        self.spin.setValue(min(current, available))
        self.info.setText(
            f"候选细胞：{available} 个（总细胞 {self.total_count}，未计数 {self.uncounted_count}）")

    def count(self) -> int:
        return int(self.spin.value())

    def only_from_uncounted(self) -> bool:
        return bool(self.only_uncounted.isChecked())
