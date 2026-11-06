"""Run best detector on detection/test and write COCO-format test_predictions.json."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
TEST_INFO = ROOT / "data_pack" / "detection" / "test" / "image_info.json"
TEST_DIR = ROOT / "data_pack" / "detection" / "test" / "images"
DEFAULT_WEIGHTS = ROOT / "weights" / "best.pt"
OUT = ROOT / "test_predictions.json"


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    p.add_argument("--conf", type=float, default=0.10)
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args()

    info = json.loads(TEST_INFO.read_text())
    model = YOLO(str(args.weights))
    preds = []

    for im in info["images"]:
        path = TEST_DIR / im["file_name"]
        res = model.predict(str(path), conf=args.conf, verbose=False, device=0)[0]
        if res.boxes is None or len(res.boxes) == 0:
            # fallback: no detection — skip or emit low-score full-frame is worse; skip
            continue
        i = int(res.boxes.conf.argmax())
        x1, y1, x2, y2 = res.boxes.xyxy[i].cpu().numpy().tolist()
        score = float(res.boxes.conf[i].cpu())
        w, h = x2 - x1, y2 - y1
        preds.append(
            {
                "image_id": int(im["id"]),
                "category_id": 1,
                "bbox": [round(float(x1), 2), round(float(y1), 2), round(float(w), 2), round(float(h), 2)],
                "score": float(score),
            }
        )

    args.out.write_text(json.dumps(preds, indent=1))
    print(f"Wrote {len(preds)}/{len(info['images'])} predictions to {args.out}")


if __name__ == "__main__":
    main()
