"""Cell label store, editing operations and undo/redo history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np
from scipy import ndimage


@dataclass(frozen=True)
class CellMeta:
    origin: str      # "auto" | "manual"
    counted: bool


@dataclass
class CellStats:
    area: int
    cy: float
    cx: float
    bbox: tuple[int, int, int, int]  # (r0, r1, c0, c1)


@dataclass
class HistoryEntry:
    bbox: tuple[int, int, int, int] | None
    before_labels: np.ndarray | None
    after_labels: np.ndarray | None
    before_meta: dict[int, CellMeta]
    after_meta: dict[int, CellMeta]
    before_next: int
    after_next: int


class CellStore:
    HISTORY_LIMIT = 80

    def __init__(self, shape: tuple[int, int] | None = None):
        if shape is None:
            shape = (0, 0)
        self.labels = np.zeros(shape, np.int32)
        self.metas: dict[int, CellMeta] = {}
        self.stats: dict[int, CellStats] = {}
        self.next_id = 1
        self.history: list[HistoryEntry] = []
        self.history_index = 0

    # ------------------------------------------------------------------ basics
    @property
    def shape(self) -> tuple[int, int]:
        return int(self.labels.shape[0]), int(self.labels.shape[1])

    @property
    def has_cells(self) -> bool:
        return bool(self.metas)

    def __len__(self) -> int:
        return len(self.metas)

    def counted_ids(self) -> list[int]:
        return [cid for cid, m in self.metas.items() if m.counted]

    def numbering(self) -> list[int]:
        ids = self.counted_ids()
        ids.sort(key=lambda cid: (
            self.stats[cid].cy if cid in self.stats else 0.0,
            self.stats[cid].cx if cid in self.stats else 0.0,
            cid,
        ))
        return ids

    def number_map(self) -> dict[int, int]:
        return {cid: i + 1 for i, cid in enumerate(self.numbering())}

    def spatially_uniform_sample(self, n: int, candidate_ids: Iterable[int] | None = None,
                                 seed: int | None = None) -> list[int]:
        """Random sample with weighted farthest-point sampling.

        The first cell is uniformly random; each next cell is drawn with
        probability proportional to squared distance from the nearest already
        selected cell (k-means++ style). This keeps the sample spread out while
        retaining randomness.
        """
        if n <= 0:
            return []
        ids = list(candidate_ids) if candidate_ids is not None else list(self.metas)
        ids = [int(i) for i in ids if int(i) in self.stats]
        if not ids:
            return []
        if n >= len(ids):
            return ids

        rng = np.random.default_rng(seed)
        h, w = self.shape
        scale = float(max(h, w, 1))
        pts = np.asarray([
            [self.stats[cid].cx / scale, self.stats[cid].cy / scale]
            for cid in ids
        ], dtype=np.float64)

        first = int(rng.integers(len(ids)))
        selected = [first]
        selected_mask = np.zeros(len(ids), dtype=bool)
        selected_mask[first] = True
        dist2 = np.sum((pts - pts[first]) ** 2, axis=1)

        while len(selected) < n:
            weights = dist2.astype(np.float64, copy=True)
            weights[selected_mask] = 0.0
            total = float(weights.sum())
            if total > 0.0:
                nxt = int(rng.choice(len(ids), p=weights / total))
            else:
                remaining = np.flatnonzero(~selected_mask)
                if remaining.size == 0:
                    break
                nxt = int(rng.choice(remaining))
            if selected_mask[nxt]:
                remaining = np.flatnonzero(~selected_mask)
                if remaining.size == 0:
                    break
                nxt = int(rng.choice(remaining))
            selected.append(nxt)
            selected_mask[nxt] = True
            dist2 = np.minimum(dist2, np.sum((pts - pts[nxt]) ** 2, axis=1))

        return [ids[i] for i in selected]

    def status(self, cid: int) -> str:
        m = self.metas.get(cid)
        if m is None:
            return "none"
        if m.counted:
            return "counted"
        return "manual_uncounted" if m.origin == "manual" else "auto_uncounted"

    def stats_of(self, cid: int) -> CellStats | None:
        return self.stats.get(cid)

    # --------------------------------------------------------------- load data
    def set_from_mask(self, mask: np.ndarray, count_all: bool) -> int:
        mask = np.asarray(mask)
        if mask.ndim != 2:
            raise ValueError("掩膜必须是二维数组")
        if self.labels.shape != mask.shape:
            self.labels = np.zeros(mask.shape, np.int32)
        else:
            self.labels.fill(0)
        self.metas.clear()
        self.stats.clear()
        self.next_id = 1
        self.history.clear()
        self.history_index = 0

        if mask.size == 0 or mask.max() <= 0:
            return 0
        mask_i = mask.astype(np.int64, copy=False)
        uniq = np.unique(mask_i)
        uniq = uniq[uniq > 0]
        if uniq.size == 0:
            return 0
        maxv = int(mask_i.max())
        remap = np.zeros(maxv + 1, np.int32)
        remap[uniq] = np.arange(1, uniq.size + 1, dtype=np.int32)
        self.labels[...] = remap[mask_i]
        self.metas = {
            int(i): CellMeta("auto", bool(count_all))
            for i in range(1, int(uniq.size) + 1)
        }
        self.next_id = int(uniq.size) + 1
        self.recompute_stats()
        return int(uniq.size)

    def load_session(self, labels: np.ndarray, origins: dict[int, str],
                     counted: set[int], next_id: int) -> None:
        self.labels = np.asarray(labels, np.int32).copy()
        self.metas = {
            int(cid): CellMeta(str(origins.get(cid, "auto")),
                               bool(int(cid) in counted))
            for cid in np.unique(self.labels) if cid > 0
        }
        self.next_id = max(int(next_id), int(self.labels.max()) + 1 if self.labels.size else 1)
        self.stats.clear()
        self.history.clear()
        self.history_index = 0
        self.recompute_stats()

    def clear_cells(self) -> None:
        self.labels.fill(0)
        self.metas.clear()
        self.stats.clear()
        self.next_id = 1
        self.history.clear()
        self.history_index = 0

    # ---------------------------------------------------------------- editing
    def add_polygon(self, points: np.ndarray, counted: bool = True) -> int | None:
        if points is None or len(points) < 3:
            return None
        h, w = self.shape
        pts = np.asarray(points, dtype=np.float64)
        x0 = max(0, int(np.floor(pts[:, 0].min())) - 1)
        y0 = max(0, int(np.floor(pts[:, 1].min())) - 1)
        x1 = min(w, int(np.ceil(pts[:, 0].max())) + 2)
        y1 = min(h, int(np.ceil(pts[:, 1].max())) + 2)
        if x1 - x0 < 2 or y1 - y0 < 2:
            return None

        local = np.zeros((y1 - y0, x1 - x0), np.uint8)
        local_pts = np.stack([pts[:, 0] - x0, pts[:, 1] - y0], axis=1)
        cv2.fillPoly(local, [np.round(local_pts).astype(np.int32)], 1)
        if int(local.sum()) < 8:
            return None

        bbox = (y0, y1, x0, x1)
        before_labels = self.labels[bbox[0]:bbox[1], bbox[2]:bbox[3]].copy()
        before_meta = dict(self.metas)
        before_next = self.next_id

        new_id = self.next_id
        self.next_id += 1
        roi = self.labels[bbox[0]:bbox[1], bbox[2]:bbox[3]]
        region = local.astype(bool)
        roi[region] = 0
        roi[region] = new_id
        self.metas[new_id] = CellMeta("manual", bool(counted))

        self.recompute_stats()
        self._drop_empty()
        self._push_history(bbox, before_labels, before_meta, before_next)
        return new_id

    def delete_cells(self, ids: Iterable[int]) -> int:
        ids = {int(i) for i in ids if int(i) in self.metas}
        if not ids:
            return 0
        boxes = [self.stats[i].bbox for i in ids if i in self.stats]
        if not boxes:
            return 0
        r0 = min(b[0] for b in boxes)
        r1 = max(b[1] for b in boxes)
        c0 = min(b[2] for b in boxes)
        c1 = max(b[3] for b in boxes)
        bbox = (max(0, r0), min(self.shape[0], r1),
                max(0, c0), min(self.shape[1], c1))
        if bbox[1] <= bbox[0] or bbox[3] <= bbox[2]:
            return 0
        before_labels = self.labels[bbox[0]:bbox[1], bbox[2]:bbox[3]].copy()
        before_meta = dict(self.metas)
        before_next = self.next_id

        roi = self.labels[bbox[0]:bbox[1], bbox[2]:bbox[3]]
        roi[np.isin(roi, list(ids))] = 0
        for cid in ids:
            self.metas.pop(cid, None)
        self.recompute_stats()
        self._drop_empty()
        self._push_history(bbox, before_labels, before_meta, before_next)
        return len(ids)

    def set_counted(self, ids: Iterable[int], value: bool) -> int:
        ids = [int(i) for i in ids if int(i) in self.metas]
        ids = [i for i in ids if self.metas[i].counted != bool(value)]
        if not ids:
            return 0
        before_meta = dict(self.metas)
        before_next = self.next_id
        for cid in ids:
            m = self.metas[cid]
            self.metas[cid] = CellMeta(m.origin, bool(value))
        self._push_history(None, None, before_meta, before_next)
        return len(ids)

    def toggle_counted(self, cid: int) -> int:
        if cid not in self.metas:
            return 0
        return self.set_counted([cid], not self.metas[cid].counted)

    def _drop_empty(self) -> None:
        empty = [cid for cid in self.metas
                 if cid not in self.stats or self.stats[cid].area <= 0]
        for cid in empty:
            self.metas.pop(cid, None)
            self.stats.pop(cid, None)

    # ------------------------------------------------------------------ stats
    def recompute_stats(self) -> None:
        self.stats.clear()
        if self.labels.size == 0:
            return
        # scipy.ndimage.find_objects returns index 0 for label 1.
        objects = ndimage.find_objects(self.labels)
        for cid in list(self.metas.keys()):
            if cid <= 0 or (cid - 1) >= len(objects):
                continue
            sl = objects[cid - 1]
            if sl is None:
                continue
            local = self.labels[sl] == cid
            area = int(local.sum())
            if area <= 0:
                continue
            ys, xs = np.nonzero(local)
            cy = float(ys.mean()) + sl[0].start
            cx = float(xs.mean()) + sl[1].start
            self.stats[cid] = CellStats(
                area=area,
                cy=cy,
                cx=cx,
                bbox=(sl[0].start, sl[0].stop, sl[1].start, sl[1].stop),
            )

    # ---------------------------------------------------------------- history
    def _push_history(self, bbox, before_labels, before_meta, before_next) -> None:
        if self.history_index < len(self.history):
            self.history = self.history[:self.history_index]
        after_labels = self.labels[bbox[0]:bbox[1], bbox[2]:bbox[3]].copy() if bbox is not None else None
        entry = HistoryEntry(
            bbox=bbox,
            before_labels=before_labels,
            after_labels=after_labels,
            before_meta=before_meta,
            after_meta=dict(self.metas),
            before_next=before_next,
            after_next=self.next_id,
        )
        self.history.append(entry)
        if len(self.history) > self.HISTORY_LIMIT:
            self.history.pop(0)
        self.history_index = len(self.history)

    @property
    def can_undo(self) -> bool:
        return self.history_index > 0

    @property
    def can_redo(self) -> bool:
        return self.history_index < len(self.history)

    def undo(self) -> bool:
        if not self.can_undo:
            return False
        self.history_index -= 1
        e = self.history[self.history_index]
        if e.bbox is not None and e.before_labels is not None:
            self.labels[e.bbox[0]:e.bbox[1], e.bbox[2]:e.bbox[3]] = e.before_labels
        self.metas = dict(e.before_meta)
        self.next_id = e.before_next
        self.recompute_stats()
        return True

    def redo(self) -> bool:
        if not self.can_redo:
            return False
        e = self.history[self.history_index]
        if e.bbox is not None and e.after_labels is not None:
            self.labels[e.bbox[0]:e.bbox[1], e.bbox[2]:e.bbox[3]] = e.after_labels
        self.metas = dict(e.after_meta)
        self.next_id = e.after_next
        self.recompute_stats()
        self.history_index += 1
        return True

    # ----------------------------------------------------------------- export
    def export_label_mask(self) -> tuple[np.ndarray, list[int]]:
        ids = self.numbering()
        if len(ids) > 65535:
            raise RuntimeError("细胞数量超过 65535，无法写入 16-bit 标签图。")
        out = np.zeros(self.shape, np.uint16)
        if not ids:
            return out, []
        max_label = max(int(self.labels.max()), self.next_id - 1) + 1
        remap = np.zeros(max_label, np.uint16)
        remap[np.asarray(ids, np.int64)] = np.arange(1, len(ids) + 1, dtype=np.uint16)
        out[...] = remap[self.labels]
        return out, ids

    def pixel_area(self, cid: int) -> int:
        st = self.stats.get(cid)
        return int(st.area) if st else 0
