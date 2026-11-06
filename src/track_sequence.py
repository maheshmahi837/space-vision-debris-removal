"""
Bonus I: feature extraction and target tracking on the SPARK sequence.

Pipeline
1. Initialize the target box with the trained detector on frame 1.
2. Extract Shi-Tomasi corners inside the box and track them with
   pyramidal Lucas-Kanade optical flow (frame-to-frame correspondences).
3. Update the box from the median feature motion. Re-detect with YOLO
   when too few features survive, and keep the detection if it agrees
   with the track (IoU) or the track has collapsed.
4. Save an annotated montage, a trajectory plot, and per-frame boxes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
SEQ_DIR = ROOT / "data_pack" / "tracking" / "sequence" / "images"
INFO = ROOT / "data_pack" / "tracking" / "sequence" / "image_info.json"
CAM = ROOT / "data_pack" / "camera.json"
WEIGHTS = ROOT / "weights" / "best.pt"
OUT = ROOT / "results" / "tracking"


def detect_box(model: YOLO, path: Path, conf: float = 0.15) -> tuple[np.ndarray | None, float]:
    res = model.predict(str(path), conf=conf, imgsz=640, verbose=False, device=0)[0]
    if res.boxes is None or len(res.boxes) == 0:
        return None, 0.0
    i = int(res.boxes.conf.argmax())
    x1, y1, x2, y2 = res.boxes.xyxy[i].cpu().numpy()
    return np.array([x1, y1, x2 - x1, y2 - y1], dtype=np.float64), float(res.boxes.conf[i])


def iou_xywh(a: np.ndarray, b: np.ndarray) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2, bx2, by2 = ax1 + aw, ay1 + ah, bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = aw * ah + bw * bh - inter + 1e-9
    return float(inter / union)


def corners_in_box(gray: np.ndarray, box: np.ndarray, max_corners: int = 80) -> np.ndarray | None:
    x, y, w, h = box
    H, W = gray.shape
    x1, y1 = int(max(0, x)), int(max(0, y))
    x2, y2 = int(min(W - 1, x + w)), int(min(H - 1, y + h))
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None
    roi = gray[y1:y2, x1:x2]
    pts = cv2.goodFeaturesToTrack(
        roi,
        maxCorners=max_corners,
        qualityLevel=0.01,
        minDistance=7,
        blockSize=7,
    )
    if pts is None:
        return None
    pts = pts.reshape(-1, 2)
    pts[:, 0] += x1
    pts[:, 1] += y1
    return pts.astype(np.float32)


def track_points(prev: np.ndarray, curr: np.ndarray, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(
        prev,
        curr,
        pts.reshape(-1, 1, 2),
        None,
        winSize=(21, 21),
        maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    if nxt is None:
        return np.empty((0, 2), np.float32), np.empty((0, 2), np.float32)
    status = status.reshape(-1).astype(bool)
    return pts[status], nxt.reshape(-1, 2)[status]


def box_from_flow(box: np.ndarray, src: np.ndarray, dst: np.ndarray, shape: tuple[int, int]) -> np.ndarray | None:
    if len(src) < 6:
        return None
    disp = dst - src
    # reject outlier motions
    med = np.median(disp, axis=0)
    resid = np.linalg.norm(disp - med, axis=1)
    keep = resid < max(8.0, np.median(resid) * 2.5 + 2.0)
    if keep.sum() < 4:
        return None
    dx, dy = np.median(disp[keep], axis=0)
    x, y, w, h = box
    H, W = shape
    x, y = float(x + dx), float(y + dy)
    x = float(np.clip(x, 0, W - 2))
    y = float(np.clip(y, 0, H - 2))
    w = float(min(w, W - x))
    h = float(min(h, H - y))
    return np.array([x, y, w, h], dtype=np.float64)


def draw_box(img: np.ndarray, box: np.ndarray, text: str, color=(0, 255, 0)) -> None:
    x, y, w, h = [int(round(v)) for v in box]
    cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
    cx, cy = x + w // 2, y + h // 2
    cv2.drawMarker(img, (cx, cy), color, cv2.MARKER_CROSS, 16, 2)
    cv2.putText(img, text, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    vis_dir = OUT / "frames"
    vis_dir.mkdir(exist_ok=True)

    info = json.loads(INFO.read_text())
    cam = json.loads(CAM.read_text())
    cam_fx, cam_fy = float(cam["fx"]), float(cam["fy"])
    cam_cx, cam_cy = float(cam["cx"]), float(cam["cy"])
    frames = sorted(info["images"], key=lambda im: im["frame_id"])
    model = YOLO(str(WEIGHTS))

    records = []
    prev_gray = None
    pts = None
    box = None
    n_redetect = 0
    n_flow_fail = 0

    for im in frames:
        path = SEQ_DIR / im["file_name"]
        bgr = cv2.imread(str(path))
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        fid = int(im["frame_id"])
        source = "init"

        if box is None:
            det, score = detect_box(model, path, conf=0.05)
            if det is None:
                raise RuntimeError(f"Detector failed to initialize on {im['file_name']}")
            box, source = det, "detect"
            pts = corners_in_box(gray, box)
        else:
            src, dst = (np.empty((0, 2)), np.empty((0, 2)))
            if pts is not None and len(pts) >= 6:
                src, dst = track_points(prev_gray, gray, pts)
            moved = box_from_flow(box, src, dst, gray.shape)
            if moved is None:
                n_flow_fail += 1
                det, score = detect_box(model, path, conf=0.05)
                if det is not None:
                    box, source = det, "redetect"
                    n_redetect += 1
                else:
                    source = "coast"
            else:
                box = moved
                source = "flow"
                # refresh from detector when the track looks thin or every 15 frames
                if len(dst) < 12 or fid % 15 == 0:
                    det, score = detect_box(model, path, conf=0.10)
                    if det is not None and iou_xywh(det, box) >= 0.3:
                        # blend toward the detection to limit drift
                        box = 0.35 * box + 0.65 * det
                        source = "flow+detect"
                        n_redetect += 1
                    elif det is not None and len(dst) < 8:
                        box, source = det, "redetect"
                        n_redetect += 1
            pts = corners_in_box(gray, box)

        cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
        # Line of sight from the box centre. Distortion is not in camera.json.
        xn = (cx - cam_cx) / cam_fx
        yn = (cy - cam_cy) / cam_fy
        records.append(
            {
                "frame_id": fid,
                "file_name": im["file_name"],
                "bbox": [round(float(v), 2) for v in box],
                "centroid": [round(float(cx), 2), round(float(cy), 2)],
                "los_xy": [round(float(xn), 5), round(float(yn), 5)],
                "angle_from_boresight_deg": round(math.degrees(math.atan(math.hypot(xn, yn))), 3),
                "n_features": 0 if pts is None else int(len(pts)),
                "source": source,
            }
        )

        if fid == 1 or fid % 30 == 0 or fid == len(frames):
            vis = bgr.copy()
            draw_box(vis, box, f"f{fid} {source} n={0 if pts is None else len(pts)}")
            cv2.imwrite(str(vis_dir / f"track_{fid:04d}.jpg"), vis)

        prev_gray = gray

    (OUT / "track.json").write_text(json.dumps(records, indent=1))

    xs = [r["centroid"][0] for r in records]
    ys = [r["centroid"][1] for r in records]
    fids = [r["frame_id"] for r in records]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(xs, ys, "-o", ms=2, lw=1)
    axes[0].set_title("Image-plane centroid track")
    axes[0].set_xlabel("x (px)")
    axes[0].set_ylabel("y (px)")
    axes[0].invert_yaxis()
    axes[0].set_aspect("equal", adjustable="box")
    axes[1].plot(fids, xs, label="cx")
    axes[1].plot(fids, ys, label="cy")
    axes[1].set_title("Centroid vs frame")
    axes[1].set_xlabel("frame")
    axes[1].legend()
    plt.tight_layout()
    plt.savefig(OUT / "trajectory.png", dpi=130)

    # montage of saved frames
    saved = sorted(vis_dir.glob("track_*.jpg"))
    cols = 4
    rows = int(np.ceil(len(saved) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(14, 3.2 * rows))
    for ax, p in zip(np.atleast_1d(axes).ravel(), saved):
        ax.imshow(cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB))
        ax.set_title(p.stem, fontsize=8)
        ax.axis("off")
    for ax in np.atleast_1d(axes).ravel()[len(saved) :]:
        ax.axis("off")
    plt.tight_layout()
    plt.savefig(OUT / "tracking_montage.png", dpi=110)

    summary = {
        "n_frames": len(records),
        "n_flow_fail": n_flow_fail,
        "n_detector_updates": n_redetect,
        "mean_features": float(np.mean([r["n_features"] for r in records])),
        "centroid_start": records[0]["centroid"],
        "centroid_end": records[-1]["centroid"],
        "path_length_px": float(np.sum(np.hypot(np.diff(xs), np.diff(ys)))),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
