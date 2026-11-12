"""Image loading, channel handling and display composition."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

try:
    import tifffile
except Exception:  # pragma: no cover
    tifffile = None

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


IMAGE_EXTENSIONS = (
    ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp",
)


@dataclass
class LoadedImage:
    path: Path
    raw: np.ndarray                 # (C, H, W), native dtype
    display_channels: np.ndarray    # (C, H, W), uint8, contrast stretched
    display_rgb: np.ndarray         # (H, W, 3), uint8
    channel_names: list[str]
    is_rgb_like: bool = False
    warning: str = ""

    @property
    def height(self) -> int:
        return int(self.display_rgb.shape[0])

    @property
    def width(self) -> int:
        return int(self.display_rgb.shape[1])

    @property
    def n_channels(self) -> int:
        return int(self.display_channels.shape[0])

    @property
    def info_text(self) -> str:
        bits = self.raw.dtype.itemsize * 8
        kind = "RGB" if self.is_rgb_like else ("灰度" if self.n_channels == 1 else f"{self.n_channels} 通道")
        return f"{self.width} × {self.height} px · {kind} · {bits}-bit"

    def auto_seg_channel(self) -> int:
        """0-based channel used by 'auto' segmentation.

        For RGB and multi-channel images the second channel (green / membrane)
        is a sensible default for whole-cell segmentation.
        """
        if self.n_channels == 1:
            return 0
        return 1

    def channel_display_name(self, idx: int) -> str:
        if 0 <= idx < len(self.channel_names):
            return self.channel_names[idx]
        return f"通道 {idx + 1}"


def _read_array(path: Path) -> np.ndarray:
    ext = path.suffix.lower()
    if ext in (".tif", ".tiff"):
        if tifffile is None:
            raise RuntimeError("缺少 tifffile，无法读取 TIFF。")
        return tifffile.imread(str(path))
    if cv2 is None:
        raise RuntimeError("缺少 OpenCV，无法读取该图像。")
    arr = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if arr is None:
        raise RuntimeError(f"无法读取图像：{path}")
    if arr.ndim == 3 and arr.shape[2] >= 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    return arr


def _canonicalize(arr: np.ndarray):
    """Return (C,H,W) array and metadata.

    Handles grayscale, RGB(A), channel-first multi-channel and simple stacks.
    """
    warning = ""
    if arr.ndim == 2:
        return arr[None, ...], False, warning
    if arr.ndim == 4:
        # Z/Y/X/C or Z/C/Y/X. Show the first plane.
        if arr.shape[-1] in (3, 4) and arr.shape[0] > 4 and arr.shape[1] > 4:
            arr = arr[0]
        elif arr.shape[0] > 4:
            arr = arr[0]
        else:
            arr = arr[0]
        warning = "检测到多维图像，当前仅显示/分析第一个平面。"
        if arr.ndim == 2:
            return arr[None, ...], False, warning
    if arr.ndim != 3:
        raise RuntimeError(f"不支持的图像维度：{arr.shape}")

    d0, d1, d2 = arr.shape
    # RGB(A) stored as (H, W, C)
    if d2 in (3, 4) and d0 > 4 and d1 > 4:
        rgb = arr[:, :, :3]
        return np.transpose(rgb, (2, 0, 1)), True, warning

    # Channel-first (C, H, W)
    if d0 in (2, 3, 4) and d1 > 4 and d2 > 4:
        return arr[:4], False, warning

    # (H, W, 2) or other small-last-axis layouts
    if d2 in (2, 3, 4) and d0 > 4 and d1 > 4:
        rgb = arr[:, :, :d2]
        return np.transpose(rgb, (2, 0, 1)), d2 == 3, warning

    # Z-stack (Z, H, W): use first plane
    if d0 > 4 and d1 > 4 and d2 > 4:
        return arr[:1], False, "检测到 Z 轴堆栈，当前仅分析第一个平面。"

    raise RuntimeError(f"无法解析图像维度：{arr.shape}")


def _stretch(ch: np.ndarray) -> np.ndarray:
    if ch.dtype == np.uint8:
        lo = float(ch.min())
        hi = float(ch.max())
        if lo == 0.0 and hi == 255.0:
            return ch.copy()
    a = ch.astype(np.float32, copy=False)
    if a.size == 0:
        return np.zeros(a.shape, np.uint8)
    lo, hi = np.percentile(a, (0.5, 99.5))
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        lo, hi = float(a.min()), float(a.max())
    if hi <= lo:
        return np.zeros(a.shape, np.uint8)
    out = np.clip((a - lo) * (255.0 / (hi - lo)), 0, 255)
    return out.astype(np.uint8)


def _compose(display_channels: np.ndarray, is_rgb_like: bool):
    c = display_channels.shape[0]
    h, w = display_channels.shape[1:]
    rgb = np.zeros((h, w, 3), np.uint8)
    if c == 1:
        rgb[...] = display_channels[0][..., None]
        return rgb
    if is_rgb_like:
        rgb[...] = np.transpose(display_channels[:3], (1, 2, 0))
        return rgb
    if c == 2:
        # channel 1 -> blue, channel 2 -> green
        rgb[..., 2] = display_channels[0]
        rgb[..., 1] = display_channels[1]
        return rgb
    if c == 3:
        # DAPI-like / FITC-like / TRITC-like
        rgb[..., 2] = display_channels[0]
        rgb[..., 1] = display_channels[1]
        rgb[..., 0] = display_channels[2]
        return rgb
    # 4+ channels: blue, green, red, magenta
    rgb[..., 2] = display_channels[0]
    rgb[..., 1] = display_channels[1]
    rgb[..., 0] = display_channels[2]
    magenta = display_channels[3]
    rgb[..., 0] = np.maximum(rgb[..., 0], (magenta * 0.75).astype(np.uint8))
    rgb[..., 2] = np.maximum(rgb[..., 2], (magenta * 0.75).astype(np.uint8))
    return rgb


def load_image(path: os.PathLike | str) -> LoadedImage:
    p = Path(path)
    arr = _read_array(p)
    raw, is_rgb_like, warning = _canonicalize(arr)
    if raw.dtype == np.bool_:
        raw = raw.astype(np.uint8)
    if raw.ndim != 3 or raw.shape[1] < 2 or raw.shape[2] < 2:
        raise RuntimeError("图像尺寸无效。")
    if raw.shape[0] > 8:
        raise RuntimeError(f"通道数过多（{raw.shape[0]}），暂不支持。")

    display_channels = np.stack([_stretch(ch) for ch in raw], axis=0)
    display_rgb = _compose(display_channels, is_rgb_like)

    if is_rgb_like:
        names = ["红 (R)", "绿 (G)", "蓝 (B)"][: raw.shape[0]]
    elif raw.shape[0] == 1:
        names = ["灰度"]
    elif raw.shape[0] == 2:
        names = ["通道 1", "通道 2"]
    else:
        names = [f"通道 {i + 1}" for i in range(raw.shape[0])]

    return LoadedImage(
        path=p,
        raw=raw,
        display_channels=display_channels,
        display_rgb=display_rgb,
        channel_names=names,
        is_rgb_like=is_rgb_like,
        warning=warning,
    )
