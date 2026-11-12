"""Customisable overlay colours, opacity and edge width."""

from __future__ import annotations

from dataclasses import dataclass, field

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor

from . import theme

SETTINGS_ORG = "SimpleCellSegmentation"
SETTINGS_APP = "SimpleCellSegmentation"


def _color(value, fallback: str) -> QColor:
    color = QColor(value)
    if not color.isValid():
        color = QColor(fallback)
    return color


@dataclass
class OverlayStyle:
    counted_edge: QColor = field(default_factory=lambda: QColor(theme.YELLOW))
    counted_fill: QColor = field(default_factory=lambda: QColor(theme.YELLOW))
    auto_edge: QColor = field(default_factory=lambda: QColor(theme.WHITE))
    auto_fill: QColor = field(default_factory=lambda: QColor(theme.WHITE))
    manual_edge: QColor = field(default_factory=lambda: QColor(theme.GRAY))
    manual_fill: QColor = field(default_factory=lambda: QColor(theme.GRAY))
    edge_opacity: int = 93
    fill_opacity: int = 18
    edge_width: int = 2
    fill_enabled: bool = False

    def copy(self) -> "OverlayStyle":
        return OverlayStyle(
            counted_edge=QColor(self.counted_edge),
            counted_fill=QColor(self.counted_fill),
            auto_edge=QColor(self.auto_edge),
            auto_fill=QColor(self.auto_fill),
            manual_edge=QColor(self.manual_edge),
            manual_fill=QColor(self.manual_fill),
            edge_opacity=int(self.edge_opacity),
            fill_opacity=int(self.fill_opacity),
            edge_width=int(self.edge_width),
            fill_enabled=bool(self.fill_enabled),
        )

    @classmethod
    def load(cls) -> "OverlayStyle":
        default = cls()
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        return cls(
            counted_edge=_color(s.value("style/counted_edge", default.counted_edge.name()),
                                theme.YELLOW),
            counted_fill=_color(s.value("style/counted_fill", default.counted_fill.name()),
                                theme.YELLOW),
            auto_edge=_color(s.value("style/auto_edge", default.auto_edge.name()),
                             theme.WHITE),
            auto_fill=_color(s.value("style/auto_fill", default.auto_fill.name()),
                             theme.WHITE),
            manual_edge=_color(s.value("style/manual_edge", default.manual_edge.name()),
                               theme.GRAY),
            manual_fill=_color(s.value("style/manual_fill", default.manual_fill.name()),
                               theme.GRAY),
            edge_opacity=max(0, min(100, int(s.value("style/edge_opacity", 93)))),
            fill_opacity=max(0, min(100, int(s.value("style/fill_opacity", 18)))),
            edge_width=max(1, min(8, int(s.value("style/edge_width", 2)))),
            fill_enabled=bool(s.value("style/fill_enabled", False, type=bool)),
        )

    def save(self) -> None:
        s = QSettings(SETTINGS_ORG, SETTINGS_APP)
        s.setValue("style/counted_edge", self.counted_edge.name())
        s.setValue("style/counted_fill", self.counted_fill.name())
        s.setValue("style/auto_edge", self.auto_edge.name())
        s.setValue("style/auto_fill", self.auto_fill.name())
        s.setValue("style/manual_edge", self.manual_edge.name())
        s.setValue("style/manual_fill", self.manual_fill.name())
        s.setValue("style/edge_opacity", int(self.edge_opacity))
        s.setValue("style/fill_opacity", int(self.fill_opacity))
        s.setValue("style/edge_width", int(self.edge_width))
        s.setValue("style/fill_enabled", bool(self.fill_enabled))
        s.sync()

    def edge_color(self, key: str) -> QColor:
        return {
            "counted": self.counted_edge,
            "auto": self.auto_edge,
            "manual": self.manual_edge,
        }[key]

    def fill_color(self, key: str) -> QColor:
        return {
            "counted": self.counted_fill,
            "auto": self.auto_fill,
            "manual": self.manual_fill,
        }[key]


def default_style() -> OverlayStyle:
    return OverlayStyle()
