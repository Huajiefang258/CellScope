"""Cellpose segmentation worker.

Runs in a separate Python process so the Qt UI stays responsive and so the
Cellpose 3 and Cellpose 4 packages never have to be imported together.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

V4_MODELS = {"cpsam_v2", "cpsam"}
V3_MODELS = {"cyto3", "cyto2", "cyto", "nuclei"}
V3_MODEL_FILES = {
    "cyto3": ("cyto3", "size_cyto3.npy"),
    "cyto2": ("cyto2torch_0", "size_cyto2torch_0.npy"),
    "cyto": ("cytotorch_0", "size_cytotorch_0.npy"),
    "nuclei": ("nucleitorch_0", "size_nucleitorch_0.npy"),
}


def emit(**payload):
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def fail(message: str, code: int = 1, **extra):
    payload = {"event": "error", "message": message}
    payload.update(extra)
    emit(**payload)
    raise SystemExit(code)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--model", default="cyto3",
                    choices=sorted(V4_MODELS | V3_MODELS))
    ap.add_argument("--source", default="auto", choices=["auto", "composite", "channel"])
    ap.add_argument("--channel", type=int, default=1, help="1-based channel index")
    ap.add_argument("--diameter", default="auto")
    ap.add_argument("--flow", type=float, default=0.4)
    ap.add_argument("--cellprob", type=float, default=0.0)
    ap.add_argument("--min-size", type=int, default=15)
    ap.add_argument("--output", required=True)
    ap.add_argument("--models-dir", default="")
    return ap.parse_args()


def models_dir(args) -> Path:
    if args.models_dir:
        return Path(args.models_dir)
    return Path.home() / ".cellpose" / "models"


def build_input(loaded, source: str, channel_1based: int):
    raw = loaded.raw
    c = raw.shape[0]
    if source == "channel":
        idx = min(max(1, channel_1based), c) - 1
        return raw[idx], [0, 0], f"通道 {idx + 1}"
    if source == "auto":
        idx = loaded.auto_seg_channel()
        return raw[idx], [0, 0], f"自动（通道 {idx + 1}）"

    # composite
    if loaded.is_rgb_like:
        rgb = raw[:3]
        if rgb.shape[0] < 3:
            pad = np.zeros((3 - rgb.shape[0],) + rgb.shape[1:], rgb.dtype)
            rgb = np.concatenate([rgb, pad], axis=0)
        rgb = rgb.transpose(1, 2, 0)
    elif c == 1:
        rgb = np.repeat(raw[0][..., None], 3, axis=2)
    elif c == 2:
        h, w = raw.shape[1:]
        rgb = np.zeros((h, w, 3), raw.dtype)
        rgb[..., 2] = raw[0]   # channel 1 -> blue
        rgb[..., 1] = raw[1]   # channel 2 -> green
    else:
        h, w = raw.shape[1:]
        rgb = np.zeros((h, w, 3), raw.dtype)
        rgb[..., 2] = raw[0]   # blue
        rgb[..., 1] = raw[1]   # green
        rgb[..., 0] = raw[2]   # red
    return rgb, [2, 3], "复合图像（蓝/绿/红）"


def run_cellpose4(args, image, channels, models_path: Path,
                  model_name: str) -> tuple:
    from cellpose import models
    import torch

    model_file = models_path / model_name
    if not model_file.exists():
        emit(event="model_missing", model=model_name, path=str(model_file))
        fail(f"{model_name} 模型不存在，请先下载模型。", 3)

    gpu = bool(torch.cuda.is_available())
    emit(event="stage", message=f"加载 {model_name} 模型…")
    model = models.CellposeModel(
        gpu=gpu,
        pretrained_model=model_name,
        use_bfloat16=gpu,
    )
    diameter = None if args.diameter == "auto" else float(args.diameter)
    emit(event="stage", message=(
        f"运行 {model_name}（CPU，可能需要 1–3 分钟）…"
        if not gpu else f"运行 {model_name}（GPU）…"
    ))
    t0 = time.time()
    masks, flows, styles = model.eval(
        image,
        diameter=diameter,
        flow_threshold=args.flow,
        cellprob_threshold=args.cellprob,
        min_size=args.min_size,
    )
    return masks, time.time() - t0, diameter


def run_cellpose3(args, image, channels, models_path: Path,
                  model_name: str) -> tuple:
    from cellpose import models
    import torch

    model_file_name, size_file_name = V3_MODEL_FILES[model_name]
    model_file = models_path / model_file_name
    size_file = models_path / size_file_name
    if not model_file.exists():
        emit(event="model_missing", model=model_name, path=str(model_file))
        fail(f"{model_name} 模型不存在，请先下载模型。", 3)
    if not size_file.exists():
        emit(event="model_missing", model=f"{model_name}_size", path=str(size_file))
        fail(f"{model_name} 尺寸模型（{size_file_name}）不存在，请先下载模型。", 3)

    gpu = bool(torch.cuda.is_available())
    emit(event="stage", message=f"加载 {model_name} 模型…")
    model = models.Cellpose(gpu=gpu, model_type=model_name)
    diameter = None if args.diameter == "auto" else float(args.diameter)
    emit(event="stage", message=(
        f"运行 {model_name}…" if not gpu else f"运行 {model_name}（GPU）…"
    ))
    t0 = time.time()
    masks, flows, styles, diams = model.eval(
        image,
        diameter=diameter,
        channels=channels,
        flow_threshold=args.flow,
        cellprob_threshold=args.cellprob,
        min_size=args.min_size,
    )
    return masks, time.time() - t0, diams


def main():
    args = parse_args()
    image_path = Path(args.image)
    if not image_path.exists():
        fail(f"找不到图像：{image_path}", 2)

    vendor_name = "cp4" if args.model in V4_MODELS else "cp3"
    vendor_dir = APP_ROOT / "vendor" / vendor_name
    if (vendor_dir / "cellpose").exists():
        sys.path.insert(0, str(vendor_dir))

    emit(event="stage", message="读取图像…")
    try:
        from cellcounter.imaging import load_image
        loaded = load_image(image_path)
    except Exception as exc:
        fail(f"读取图像失败：{exc}", 2)

    source_name = {
        "auto": "自动",
        "composite": "复合",
        "channel": f"通道 {args.channel}",
    }[args.source]
    emit(event="stage", message=f"图像：{loaded.width}×{loaded.height}，分割来源：{source_name}")

    try:
        image, channels_arg, source_desc = build_input(loaded, args.source, args.channel)
    except Exception as exc:
        fail(f"准备分割输入失败：{exc}", 2)

    mdir = models_dir(args)
    os.environ["CELLPOSE_LOCAL_MODELS_PATH"] = str(mdir)

    try:
        if args.model in V4_MODELS:
            masks, elapsed, used_diam = run_cellpose4(
                args, image, channels_arg, mdir, args.model)
        else:
            masks, elapsed, used_diam = run_cellpose3(
                args, image, channels_arg, mdir, args.model)
    except SystemExit:
        raise
    except Exception as exc:
        traceback.print_exc()
        fail(f"Cellpose 运行失败：{exc}", 4)

    masks = np.asarray(masks)
    if masks.ndim != 2:
        fail(f"Cellpose 返回了意外维度：{masks.shape}", 4)
    masks = masks.astype(np.int32, copy=False)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(out), masks)

    n = int(masks.max()) if masks.size else 0
    emit(
        event="done",
        masks=str(out),
        n_cells=n,
        shape=list(masks.shape),
        elapsed=round(float(elapsed), 2),
        diameter=(
            "auto" if used_diam is None
            else round(float(used_diam), 2) if not isinstance(used_diam, (list, tuple, np.ndarray))
            else [round(float(d), 2) for d in np.asarray(used_diam).ravel()]
        ),
        source=source_desc,
        model=args.model,
    )


if __name__ == "__main__":
    try:
        import numpy as np  # noqa: F401
    except Exception as exc:
        fail(f"缺少 numpy：{exc}", 2)
    main()
