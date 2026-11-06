"""Convert COCO detection train set to YOLO format with stratified train/val split."""
from __future__ import annotations

import json
import random
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_pack" / "detection"
OUT = ROOT / "datasets" / "spacecraft_yolo"
VAL_RATIO = 0.20
SEED = 42


def box_size_bin(bbox: list[float]) -> str:
    w, h = bbox[2], bbox[3]
    m = max(w, h)
    if m < 150:
        return "small"
    if m < 400:
        return "medium"
    return "large"


def coco_to_yolo_line(bbox: list[float], img_w: int, img_h: int, cls: int = 0) -> str:
    x, y, w, h = bbox
    cx = (x + w / 2) / img_w
    cy = (y + h / 2) / img_h
    nw = w / img_w
    nh = h / img_h
    # clip to [0,1]
    cx, cy, nw, nh = [float(np.clip(v, 0.0, 1.0)) for v in (cx, cy, nw, nh)]
    return f"{cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}"


def stratified_split(items: list[tuple], val_ratio: float, seed: int):
    """items: list of (image_dict, bbox, bin_name)"""
    by_bin: dict[str, list] = defaultdict(list)
    for it in items:
        by_bin[it[2]].append(it)

    rng = random.Random(seed)
    train, val = [], []
    for bin_name, group in by_bin.items():
        rng.shuffle(group)
        n_val = max(1, int(round(len(group) * val_ratio)))
        val.extend(group[:n_val])
        train.extend(group[n_val:])
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        dst.symlink_to(src.resolve())
    except OSError:
        shutil.copy2(src, dst)


def main() -> None:
    coco = json.loads((DATA / "train" / "annotations.json").read_text())
    images = {im["id"]: im for im in coco["images"]}
    # one ann per image
    ann_by_img = {a["image_id"]: a for a in coco["annotations"]}

    items = []
    for img_id, im in images.items():
        a = ann_by_img[img_id]
        items.append((im, a["bbox"], box_size_bin(a["bbox"])))

    train_items, val_items = stratified_split(items, VAL_RATIO, SEED)
    print(f"Split: train={len(train_items)} val={len(val_items)}")
    for name, subset in ("train", train_items), ("val", val_items):
        counts = defaultdict(int)
        for _, _, b in subset:
            counts[b] += 1
        print(f"  {name} bins: {dict(counts)}")

    if OUT.exists():
        shutil.rmtree(OUT)

    img_src = DATA / "train" / "images"
    for split, subset in ("train", train_items), ("val", val_items):
        for im, bbox, _ in subset:
            link_or_copy(img_src / im["file_name"], OUT / "images" / split / im["file_name"])
            label = coco_to_yolo_line(bbox, im["width"], im["height"])
            lp = OUT / "labels" / split / (Path(im["file_name"]).stem + ".txt")
            lp.parent.mkdir(parents=True, exist_ok=True)
            lp.write_text(label + "\n")

    # Keep id maps for evaluation / submission
    meta = {
        "seed": SEED,
        "val_ratio": VAL_RATIO,
        "train_image_ids": [im["id"] for im, _, _ in train_items],
        "val_image_ids": [im["id"] for im, _, _ in val_items],
        "file_to_id": {im["file_name"]: im["id"] for im in coco["images"]},
    }
    (OUT / "split_meta.json").write_text(json.dumps(meta, indent=2))

    yaml_path = OUT / "data.yaml"
    yaml_path.write_text(
        yaml.dump(
            {
                "path": str(OUT.resolve()),
                "train": "images/train",
                "val": "images/val",
                "names": {0: "spacecraft"},
                "nc": 1,
            },
            sort_keys=False,
        )
    )
    print(f"Wrote dataset to {OUT}")
    print(f"data.yaml -> {yaml_path}")


if __name__ == "__main__":
    main()
