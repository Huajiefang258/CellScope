"""SimpleCellSegmentation entry point."""

from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

APP_ROOT = Path(__file__).resolve().parent
LOG_PATH = APP_ROOT / "simplecellsegmentation.log"


def setup_logging():
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    try:
        fh = RotatingFileHandler(LOG_PATH, maxBytes=2_000_000, backupCount=2,
                                 encoding="utf-8")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception:
        pass
    if sys.stderr is not None:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        log.addHandler(sh)


def main():
    setup_logging()
    log = logging.getLogger("simplecellsegmentation")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("SimpleCellSegmentation")
    app.setOrganizationName("SimpleCellSegmentation")
    app.setStyle("Fusion")

    from cellcounter import theme
    from cellcounter.mainwindow import MainWindow

    app.setStyleSheet(theme.STYLESHEET)
    app.setFont(theme.app_font(10))

    def excepthook(exc_type, exc_value, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, tb)
            return
        text = "".join(traceback.format_exception(exc_type, exc_value, tb))
        log.error("Unhandled exception:\n%s", text)
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("SimpleCellSegmentation 发生错误")
            box.setText(str(exc_value))
            box.setDetailedText(text)
            box.exec_()
        except Exception:
            pass

    sys.excepthook = excepthook

    win = MainWindow()
    win.show()
    log.info("SimpleCellSegmentation started")
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
