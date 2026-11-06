# Task 3: Image Preprocessing & Target Detection

## Method
- **Model:** YOLOv8s (COCO-pretrained), single class `spacecraft`
- **Split:** stratified 80/20 train/val on box size (480 / 120); **test (100)** held out for submission only
- **Input:** 640×640; AMP disabled on GTX 1650 (Ultralytics NaN safeguard)

## Regularization & robustness
| Technique | Setting |
|---|---|
| Optimizer | AdamW, `weight_decay=0.0015` |
| LR schedule | cosine, `lr0=0.0008`, warmup 5 epochs |
| Dropout | 0.2 |
| Label smoothing | 0.05 |
| Backbone freeze | first 10 layers |
| Mosaic / MixUp / Copy-paste | 1.0 / 0.2 / 0.15 |
| Random erasing | 0.35 |
| RandAugment | on |
| Geometric + HSV | strong scale/brightness (match dark test) |
| Albumentations | Blur, MedianBlur, CLAHE, ToGray |
| Early stopping | patience 40 on fitness |
| Checkpoints | `best.pt`, `last.pt`, every 10 epochs |

## Loss
Ultralytics detection loss (weighted sum):
- **Box:** CIoU loss (`box=8.0` gain — localization / IoU & centroid)
- **Cls:** BCE with label smoothing (`cls=0.6`)
- **DFL:** Distribution Focal Loss (`dfl=1.5`)

## Metrics (validation, 120 images, confidence 0.15)
Ground truth exists only on this split. Centroid is the box centre `(x + w/2, y + h/2)`.

| Metric | Value |
|---|---|
| Mean IoU | 0.727 |
| Median IoU | 0.762 |
| Detection rate (IoU ≥ 0.5) | 94.2% (113/120) |
| Median centroid error | 13.3 px |
| Mean centroid error | 29.1 px |
| mAP50 / mAP50-95 | 0.975 / 0.549 |

The mean centroid error is higher than the median because a missed box is counted as a large error.

## Test split (100 images, no labels in the pack)
`test_predictions.json` has one box on every image. Scores: mean 0.65, median 0.72, max 0.88, min 0.002. 83 scores are ≥ 0.5 and 92 are ≥ 0.25. Eight are below 0.25 (image ids 82, 94, 99, 46, 36, 92, 21, 44). The three lowest (82, 94, 99) are the doubtful ones on visual check: the box sits on an empty edge or a large dark region. Higher-score frames (for example test_0008, test_0065) put the box on the spacecraft. IoU and centroid error cannot be computed here; the assessors score this file against hidden labels.

## Outputs
- Weights: `weights/best.pt`
- Validation numbers: `results/val_metrics.json`
- Test COCO results: `test_predictions.json`
- Drawn images: `results/detection_examples/` (`test_0008.jpg`, `test_0049.jpg`, `test_0065.jpg`, `test_0082.jpg`, `test_0094.jpg`, plus the validation batch and the training curves)
