"""ImageJ headless area measurement helpers."""

from __future__ import annotations

import csv
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

try:
    import tifffile
except Exception:  # pragma: no cover
    tifffile = None


@dataclass
class ImageJSetup:
    n: int
    label_path: Path
    js_path: Path
    ijm_path: Path
    temp_dir: Path
    output_dir: Path
    stem: str
    pixel_size: float


def find_imagej(app_root: Path) -> tuple[Path | None, Path | None]:
    """Locate java.exe and ij.jar. Returns (java, ij_jar)."""
    app_root = Path(app_root).resolve()
    candidates = []
    env_home = os.environ.get("IMAGEJ_HOME", "").strip()
    if env_home:
        candidates.append(Path(env_home))
    candidates.extend([
        app_root,
        app_root / "ImageJ",
        app_root.parent,
        app_root.parent / "ImageJ",
    ])
    seen = set()
    for parent in candidates:
        key = str(parent).lower()
        if key in seen:
            continue
        seen.add(key)
        java = parent / "jre" / "bin" / "java.exe"
        jar = parent / "ij.jar"
        if java.exists() and jar.exists():
            return java, jar
    return None, None


def _js_string(value: str) -> str:
    return value.replace("\\", "/").replace('"', '\\"')


def prepare_measurement(label_mask: np.ndarray, output_dir: Path, stem: str,
                        pixel_size: float, temp_root: Path) -> ImageJSetup:
    if tifffile is None:
        raise RuntimeError("缺少 tifffile，无法写入 ImageJ 标签图。")
    n = int(label_mask.max())
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_root = Path(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="simplecs_ij_", dir=str(temp_root)))

    label_path = temp_dir / "labels.tif"
    # ImageJ 1.x opens uncompressed 16-bit TIFF reliably.
    tifffile.imwrite(str(label_path), label_mask.astype(np.uint16),
                     photometric="minisblack", compression=None)
    js = f"""importClass(Packages.ij.IJ);
importClass(Packages.ij.io.Opener);
importClass(Packages.ij.process.ImageProcessor);
importClass(Packages.ij.process.ImageStatistics);
importClass(Packages.ij.measure.Measurements);
importClass(Packages.ij.plugin.filter.ThresholdToSelection);

var labelPath = "{_js_string(str(label_path))}";
var nCells = {n};
var known = {float(pixel_size):.10g};
print("IJ_VERSION " + IJ.getVersion());
var imp = new Opener().openImage(labelPath);
if (imp == null) {{
    print("IJ_ERROR 无法打开标签图");
}} else {{
    var ip = imp.getProcessor();
    var cal = imp.getCalibration();
    if (known > 0) {{
        cal.pixelWidth = known;
        cal.pixelHeight = known;
        cal.setUnit("um");
    }}
    for (var i = 1; i <= nCells; i++) {{
        ip.setThreshold(i, i, ImageProcessor.NO_LUT_UPDATE);
        var roi = new ThresholdToSelection().convert(ip);
        if (roi != null) {{
            ip.setRoi(roi);
            var st = ImageStatistics.getStatistics(ip, Measurements.AREA, cal);
            print("CELL," + i + "," + st.area);
        }} else {{
            print("CELL," + i + ",0");
        }}
    }}
}}
print("IJ_DONE " + nCells);
"""
    js_path = temp_dir / "measure.js"
    js_path.write_text(js, encoding="utf-8")

    ijm = (f'code = File.openAsString("{_js_string(str(js_path))}");\n'
           'eval("js", code);\n')
    ijm_path = temp_dir / "measure.ijm"
    ijm_path.write_text(ijm, encoding="utf-8")

    return ImageJSetup(
        n=n,
        label_path=label_path,
        js_path=js_path,
        ijm_path=ijm_path,
        temp_dir=temp_dir,
        output_dir=output_dir,
        stem=stem,
        pixel_size=float(pixel_size),
    )


def write_area_csv(rows: list[tuple[int, float]], path: Path,
                   pixel_size: float, ij_version: str = "") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        if pixel_size > 0:
            w.writerow(["Cell", "Area_um2"])
        else:
            w.writerow(["Cell", "Area_px2"])
        for num, area in rows:
            w.writerow([num, f"{float(area):.3f}"])
    return path


def write_label_image(label_mask: np.ndarray, path: Path) -> Path:
    """Write a numbered label map as an ImageJ-friendly 16-bit TIFF."""
    if tifffile is None:
        raise RuntimeError("tifffile is required to write the label image.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(path), label_mask.astype(np.uint16),
                     photometric="minisblack", compression=None)
    return path


def write_annotation_image(display_rgb: np.ndarray, label_mask: np.ndarray,
                           numbers: dict[int, int], path: Path,
                           color: tuple[int, int, int] = (250, 204, 21),
                           edge_width: int = 1) -> Path:
    """Draw numbered outlines for counted cells onto the display image."""
    out = np.ascontiguousarray(display_rgb[:, :, :3]).copy()
    thickness = max(1, int(edge_width))
    # label_mask already contains sequential 1..N, so numbers are direct.
    n = int(label_mask.max()) if label_mask.size else 0
    for num in range(1, n + 1):
        ys, xs = np.nonzero(label_mask == num)
        if ys.size == 0:
            continue
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        sub = (label_mask[y0:y1, x0:x1] == num).astype(np.uint8)
        contours, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            cnt = cnt + np.array([[[x0, y0]]], dtype=cnt.dtype)
            cv2.drawContours(out, [cnt], -1, tuple(int(c) for c in color),
                             thickness, cv2.LINE_AA)
        cy = int(ys.mean())
        cx = int(xs.mean())
        text = str(num)
        scale = 0.38 if len(text) <= 3 else 0.30
        cv2.putText(out, text, (cx - 5 * len(text), cy + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(out, text, (cx - 5 * len(text), cy + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".png", cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    if not ok:
        raise RuntimeError("Could not encode the annotated PNG.")
    path.write_bytes(buf.tobytes())
    return path
