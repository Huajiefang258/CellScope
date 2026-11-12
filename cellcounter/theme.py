"""Dark microscopy-friendly theme for CellScope."""

from PyQt5.QtGui import QColor, QFont

BG = "#0B1220"
BG_DEEP = "#070D18"
PANEL = "#101827"
CARD = "#141F33"
CARD_ALT = "#182640"
BORDER = "#27364F"
BORDER_SOFT = "#1E2B42"
TEXT = "#E8EEF7"
TEXT_MUTED = "#94A3B8"
TEXT_DIM = "#64748B"
ACCENT = "#22C55E"
ACCENT_HOVER = "#16A34A"
CYAN = "#22D3EE"
YELLOW = "#FACC15"
WHITE = "#F8FAFC"
GRAY = "#9CA3AF"
BLUE = "#3B82F6"
DANGER = "#EF4444"
ORANGE = "#FB923C"

FONT_FAMILY = "Microsoft YaHei UI"
MONO_FAMILY = "Consolas"

# cell status colours
COLOR_COUNTED = QColor(YELLOW)
COLOR_AUTO_UNCUT = QColor(WHITE)
COLOR_MANUAL_UNCUT = QColor(GRAY)
COLOR_SELECTED = QColor(CYAN)
COLOR_DANGER = QColor(DANGER)

STYLESHEET = f"""
* {{
    outline: none;
}}
QMainWindow, QDialog {{
    background: {BG};
}}
QWidget {{
    color: {TEXT};
    font-family: "{FONT_FAMILY}";
    font-size: 13px;
}}
QMenuBar {{
    background: {PANEL};
    color: {TEXT_MUTED};
    border-bottom: 1px solid {BORDER_SOFT};
    padding: 2px 6px;
}}
QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 6px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {CARD_ALT};
    color: {TEXT};
}}
QMenu {{
    background: {CARD};
    border: 1px solid {BORDER};
    padding: 6px;
    border-radius: 8px;
}}
QMenu::item {{
    padding: 7px 26px 7px 22px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {CARD_ALT};
    color: {TEXT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER_SOFT};
    margin: 5px 8px;
}}
QFrame#header {{
    background: {PANEL};
    border-bottom: 1px solid {BORDER_SOFT};
}}
QFrame#card {{
    background: {CARD};
    border: 1px solid {BORDER_SOFT};
    border-radius: 12px;
}}
QLabel#appTitle {{
    color: {WHITE};
    font-size: 19px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
QLabel#appSubtitle {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QLabel#cardTitle {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#hint {{
    color: {TEXT_MUTED};
    font-size: 12px;
    line-height: 1.55;
}}
QLabel#dim {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QLabel#bigNumber {{
    color: {YELLOW};
    font-family: "{MONO_FAMILY}";
    font-size: 30px;
    font-weight: 700;
}}
QLabel#banner {{
    background: #1E3A8A;
    color: #DBEAFE;
    border: 1px solid #3B82F6;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}}
QLabel#metric {{
    color: {TEXT};
    font-family: "{MONO_FAMILY}";
    font-size: 12px;
}}
QLabel#status {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}
QPushButton {{
    background: {CARD_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: #1F3150;
    border-color: #3B4F70;
}}
QPushButton:pressed {{
    background: #16233A;
}}
QPushButton:disabled {{
    color: #5B6B83;
    background: #131D2E;
    border-color: {BORDER_SOFT};
}}
QPushButton#primary {{
    background: {ACCENT};
    color: #03150C;
    border: 1px solid {ACCENT};
    font-weight: 700;
    padding: 10px 14px;
}}
QPushButton#primary:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#primary:disabled {{
    background: #1B3A28;
    color: #6F8D7A;
    border-color: #24422F;
}}
QPushButton#ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_MUTED};
    padding: 6px 9px;
}}
QPushButton#ghost:hover {{
    background: {CARD_ALT};
    color: {TEXT};
}}
QPushButton#danger:hover {{
    background: #3A1820;
    border-color: {DANGER};
    color: #FCA5A5;
}}
QToolButton {{
    background: transparent;
    color: {TEXT_MUTED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 10px;
    font-weight: 500;
}}
QToolButton:hover {{
    background: {CARD_ALT};
    color: {TEXT};
}}
QToolButton:checked {{
    background: #15342A;
    border: 1px solid #2A6E48;
    color: #86EFAC;
}}
QToolButton#segment {{
    padding: 8px 14px;
    border-radius: 8px;
    color: {TEXT_MUTED};
}}
QToolButton#segment:checked {{
    background: {ACCENT};
    color: #052E16;
    border: 1px solid {ACCENT};
    font-weight: 700;
}}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background: {BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 6px 8px;
    min-height: 20px;
    selection-background-color: #1D4ED8;
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
    border-color: #3B4F70;
}}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    selection-background-color: #1F3150;
    padding: 4px;
}}
QCheckBox {{
    color: {TEXT_MUTED};
    spacing: 7px;
}}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 4px;
    border: 1px solid {BORDER};
    background: {BG};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QProgressBar {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 5px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {CYAN};
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
}}
QTableWidget {{
    background: {BG};
    alternate-background-color: #0E1727;
    color: {TEXT};
    border: 1px solid {BORDER_SOFT};
    border-radius: 8px;
    gridline-color: transparent;
    selection-background-color: #1E3A5F;
    selection-color: {WHITE};
}}
QHeaderView::section {{
    background: {CARD_ALT};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 6px;
    font-size: 11px;
    font-weight: 600;
}}
QTableWidget::item {{
    padding: 3px 6px;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #33445F;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #475C7D;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 9px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #33445F;
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QToolTip {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 6px 8px;
    border-radius: 6px;
}}
QSplitter::handle {{
    background: {BORDER_SOFT};
    width: 2px;
}}
QStatusBar {{
    background: {PANEL};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER_SOFT};
}}
"""


def app_font(size=10):
    f = QFont(FONT_FAMILY, size)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def mono_font(size=9, bold=False):
    f = QFont(MONO_FAMILY, size)
    f.setBold(bold)
    return f
