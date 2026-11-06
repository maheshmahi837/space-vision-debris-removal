"""
Train YOLOv8 spacecraft detector with regularization-focused settings.

Regularization / robustness levers:
- weight decay (AdamW)
- label smoothing
- dropout
- mosaic / mixup / copy-paste
- HSV + geometric aug
- domain-shift augs: blur, noise, underexposure (via Albumentations hooks + YOLO blur/noise)
- early stopping + best checkpoint by mAP50-95
- cosine LR schedule
"""
from __future__ import annotations

import json
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "datasets" / "spacecraft_yolo" / "data.yaml"
RUNS = ROOT / "runs" / "detect"
PROJECT = RUNS
NAME = "spacecraft_yolov8s"


def main() -> None:
    assert DATA_YAML.exists(), f"Missing {DATA_YAML}; run prepare_yolo_dataset.py first"

    # yolov8s: better accuracy than nano; fits GTX 1650 4GB at imgsz=640, batch=4
    model = YOLO("yolov8s.pt")

    results = model.train(
        data=str(DATA_YAML),
        epochs=150,
        imgsz=640,
        batch=4,
        device=0,
        workers=2,
        project=str(PROJECT),
        name=NAME,
        exist_ok=True,
        pretrained=True,
        optimizer="AdamW",
        lr0=0.0008,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0015,  # L2 / AdamW regularization
        warmup_epochs=5.0,
        cos_lr=True,
        # Loss gains: CIoU box + BCE/Varifocal cls + DFL (Ultralytics defaults tuned)
        # Emphasize box for IoU / centroid metrics used in the brief
        box=8.0,
        cls=0.6,
        dfl=1.5,
        label_smoothing=0.05,
        dropout=0.2,
        # Augmentation / regularization (domain shift toward darker/blurrier test)
        hsv_h=0.02,
        hsv_s=0.7,
        hsv_v=0.6,
        degrees=20.0,
        translate=0.15,
        scale=0.7,
        shear=3.0,
        perspective=0.0008,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.2,
        copy_paste=0.15,
        erasing=0.35,
        auto_augment="randaugment",
        close_mosaic=25,
        # Checkpoints + early stopping on fitness (mAP)
        patience=40,
        save=True,
        save_period=10,
        val=True,
        plots=True,
        seed=42,
        deterministic=True,
        amp=True,
        cache=False,
        rect=False,
        single_cls=True,
        freeze=10,  # freeze early backbone layers (regularization / faster adapt)
        verbose=True,
    )

    best = Path(model.trainer.best)
    last = Path(model.trainer.last)
    meta = {
        "best_weights": str(best),
        "last_weights": str(last),
        "save_dir": str(model.trainer.save_dir),
        "metrics": getattr(results, "results_dict", None) or str(results),
    }
    out = ROOT / "results" / "train_meta.json"
    out.write_text(json.dumps(meta, indent=2, default=str))
    print("Training complete.")
    print("Best:", best)
    print("Last:", last)
    print("Meta:", out)


if __name__ == "__main__":
    main()
