"""Download Cellpose model weights with progress events.

Weights are not shipped with SimpleCellSegmentation. The UI starts this script when the
user clicks "检查 / 下载当前模型". Existing partial downloads are resumed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT))

from cellcounter.models_info import MODEL_CHOICES, MODEL_FILES, MODELS_DIR

HUMAN = False
_LAST_PCT: dict[str, int] = {}


def emit(**payload):
    if not HUMAN:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return
    event = payload.get("event")
    if event == "progress":
        label = str(payload.get("label", "模型"))
        done = int(payload.get("done", 0))
        total = int(payload.get("total", 0))
        message = payload.get("message", "")
        if message and "已存在" in str(message):
            print(message, flush=True)
            return
        if total > 0:
            pct = int(done * 100 / total)
            if pct // 5 != _LAST_PCT.get(label, -1) // 5 or done >= total:
                _LAST_PCT[label] = pct
                print(f"{label}: {pct}%", flush=True)
        else:
            print(f"{label}: {done / 1e6:.0f} MB", flush=True)
    elif event == "error":
        print("下载错误：" + str(payload.get("message", "")), flush=True)
    elif event == "done":
        print(f"模型下载完成：{payload.get('model', '')}", flush=True)


def download(urls, dest: Path, label: str) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    errors = []
    for url in urls:
        for attempt in range(3):
            existing = part.stat().st_size if part.exists() else 0
            headers = {"User-Agent": "Mozilla/5.0"}
            if existing:
                headers["Range"] = f"bytes={existing}-"
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    status = getattr(resp, "status", 200)
                    total = int(resp.headers.get("Content-Length", 0) or 0)
                    if existing and status == 206:
                        mode = "ab"
                        total += existing
                    else:
                        mode = "wb"
                        existing = 0
                    emit(event="progress", label=label, done=existing,
                         total=total, message=f"正在下载 {label}")
                    with open(part, mode) as fh:
                        done = existing
                        last = 0.0
                        while True:
                            chunk = resp.read(1024 * 1024)
                            if not chunk:
                                break
                            fh.write(chunk)
                            done += len(chunk)
                            now = time.time()
                            if now - last > 0.4:
                                last = now
                                emit(event="progress", label=label, done=done,
                                     total=total)
                        if total and done < total:
                            raise IOError(f"连接中断（{done}/{total} 字节）")
                os.replace(part, dest)
                emit(event="progress", label=label, done=dest.stat().st_size,
                     total=dest.stat().st_size)
                return True
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                time.sleep(1.0 + attempt)
    emit(event="error", message="下载失败：" + " | ".join(errors[-3:]))
    return False


def main():
    global HUMAN
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=MODEL_CHOICES)
    ap.add_argument("--dest", default=str(MODELS_DIR))
    ap.add_argument("--human", action="store_true", help="print human-readable progress")
    args = ap.parse_args()
    HUMAN = args.human
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    for filename, minimum, urls in MODEL_FILES[args.model]:
        target = dest / filename
        if target.exists() and target.stat().st_size >= minimum:
            emit(event="progress", label=filename, done=target.stat().st_size,
                 total=target.stat().st_size, message=f"{filename} 已存在")
            continue
        ok = download(urls, target, filename)
        if not ok:
            return 1
        if not target.exists() or target.stat().st_size < minimum:
            emit(event="error", message=f"{filename} 文件不完整：{target}")
            return 1

    emit(event="done", model=args.model, path=str(dest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
