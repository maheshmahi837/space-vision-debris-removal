"""Validation metrics: mean IoU, detection rate (IoU>=0.5), centroid error (px)."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_pack" / "detection"
SPLIT_META = ROOT / "datasets" / "spacecraft_yolo" / "split_meta.json"
DEFAULT_WEIGHTS = ROOT / "weights" / "best.pt"


def iou_xywh(a: np.ndarray, b: np.ndarray) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter + 1e-9
    return float(inter / union)


def centroid(box: np.ndarray) -> tuple[float, float]:
    x, y, w, h = box
    return x + w / 2, y + h / 2


def predict_box(model: YOLO, image_path: Path, conf: float = 0.15):
    res = model.predict(str(image_path), conf=conf, verbose=False, device=0)[0]
    if res.boxes is None or len(res.boxes) == 0:
        return None, 0.0
    boxes = res.boxes
    # take highest-confidence detection (single-object task)
    i = int(boxes.conf.argmax())
    xyxy = boxes.xyxy[i].cpu().numpy()
    score = float(boxes.conf[i].cpu())
    x1, y1, x2, y2 = xyxy
    return np.array([x1, y1, x2 - x1, y2 - y1], dtype=np.float64), score


def evaluate(weights: Path, conf: float = 0.15) -> dict:
    coco = json.loads((DATA / "train" / "annotations.json").read_text())
    meta = json.loads(SPLIT_META.read_text())
    val_ids = set(meta["val_image_ids"])
    images = {im["id"]: im for im in coco["images"] if im["id"] in val_ids}
    gt = {a["image_id"]: np.array(a["bbox"], dtype=np.float64) for a in coco["annotations"] if a["image_id"] in val_ids}

    model = YOLO(str(weights))
    ious, cent_errs, detected = [], [], 0
    details = []

    img_dir = DATA / "train" / "images"
    for img_id, im in images.items():
        pred, score = predict_box(model, img_dir / im["file_name"], conf=conf)
        g = gt[img_id]
        if pred is None:
            ious.append(0.0)
            # large penalty for missed detection centroid
            gx, gy = centroid(g)
            cent_errs.append(float(np.hypot(gx - im["width"] / 2, gy - im["height"] / 2)))
            details.append({"image_id": img_id, "file": im["file_name"], "iou": 0.0, "score": 0.0, "miss": True})
            continue
        iou = iou_xywh(pred, g)
        ious.append(iou)
        if iou >= 0.5:
            detected += 1
        pc, gc = centroid(pred), centroid(g)
        ce = float(np.hypot(pc[0] - gc[0], pc[1] - gc[1]))
        cent_errs.append(ce)
        details.append(
            {
                "image_id": img_id,
                "file": im["file_name"],
                "iou": round(iou, 4),
                "centroid_err_px": round(ce, 2),
                "score": round(score, 4),
                "miss": False,
            }
        )

    n = len(images)
    summary = {
        "n_val": n,
        "conf_threshold": conf,
        "weights": str(weights),
        "mean_iou": float(np.mean(ious)),
        "median_iou": float(np.median(ious)),
        "detection_rate_iou50": detected / n,
        "mean_centroid_error_px": float(np.mean(cent_errs)),
        "median_centroid_error_px": float(np.median(cent_errs)),
    }
    return summary, details


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    p.add_argument("--conf", type=float, default=0.15)
    args = p.parse_args()

    summary, details = evaluate(args.weights, args.conf)
    out_dir = ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "val_metrics.json").write_text(json.dumps({"summary": summary, "details": details}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
