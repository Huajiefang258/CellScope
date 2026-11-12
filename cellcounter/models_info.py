"""Cellpose model metadata shared by the UI, worker and downloader."""

from __future__ import annotations

from pathlib import Path

MODELS_DIR = Path.home() / ".cellpose" / "models"
RECOMMENDED_MODEL = "cyto3"

V4_MODELS = {"cpsam_v2", "cpsam"}
V3_MODELS = {"cyto3", "cyto2", "cyto", "nuclei"}

MODEL_LABELS = {
    "cyto3": "cyto3 · 推荐（快速）",
    "cyto2": "cyto2（v3）",
    "cyto": "cyto（v3）",
    "nuclei": "nuclei（v3 · 细胞核）",
    "cpsam_v2": "Cellpose-SAM v2（v4 · 高精度 / 较慢）",
    "cpsam": "Cellpose-SAM v1（v4 · 旧版）",
}

MODEL_HINTS = {
    "cyto3": "推荐：CPU 速度快、通用性好，适合大多数细胞。",
    "cyto2": "较旧的细胞模型，可用于对比。",
    "cyto": "初代细胞模型，可用于对比。",
    "nuclei": "细胞核模型；请把“分割来源”改为 DAPI / 蓝色通道。",
    "cpsam_v2": "泛化能力最好，但 CPU 上明显更慢。",
    "cpsam": "旧版 Cellpose-SAM，泛化能力较好。",
}

HF_BASES = (
    "https://hf-mirror.com/mouseland/cellpose-sam/resolve/main/",
    "https://huggingface.co/mouseland/cellpose-sam/resolve/main/",
)
CELLPOSE_BASE = "https://www.cellpose.org/models/"

# model -> [(filename, minimum bytes, urls), ...]
MODEL_FILES = {
    "cyto3": [
        ("cyto3", 25 * 1024 * 1024, [CELLPOSE_BASE + "cyto3"]),
        ("size_cyto3.npy", 2000, [CELLPOSE_BASE + "size_cyto3.npy"]),
    ],
    "cyto2": [
        ("cyto2torch_0", 25 * 1024 * 1024, [CELLPOSE_BASE + "cyto2torch_0"]),
        ("size_cyto2torch_0.npy", 2000, [CELLPOSE_BASE + "size_cyto2torch_0.npy"]),
    ],
    "cyto": [
        ("cytotorch_0", 25 * 1024 * 1024, [CELLPOSE_BASE + "cytotorch_0"]),
        ("size_cytotorch_0.npy", 2000, [CELLPOSE_BASE + "size_cytotorch_0.npy"]),
    ],
    "nuclei": [
        ("nucleitorch_0", 25 * 1024 * 1024, [CELLPOSE_BASE + "nucleitorch_0"]),
        ("size_nucleitorch_0.npy", 2000, [CELLPOSE_BASE + "size_nucleitorch_0.npy"]),
    ],
    "cpsam_v2": [
        ("cpsam_v2", 1100 * 1024 * 1024, [base + "cpsam_v2" for base in HF_BASES]),
    ],
    "cpsam": [
        ("cpsam", 1100 * 1024 * 1024, [base + "cpsam" for base in HF_BASES]),
    ],
}

MODEL_CHOICES = ["cyto3", "cyto2", "cyto", "nuclei", "cpsam_v2", "cpsam"]
