# Bonus I: Feature extraction and target tracking

The sequence is 300 frames, 1440×1080, with no boxes. The camera is in `data_pack/camera.json`: fx ≈ 1745 px, fy ≈ 1747 px, principal point (720, 540). Distortion is not provided, so I treat the images as undistorted.

There are no labels, so this is checked by looking at the boxes, not by IoU.

## What I did

1. **Start the box** with the Task 3 detector on frame 1.
2. **Features:** up to 80 Shi-Tomasi corners inside the current box.
3. **Correspondences:** pyramidal Lucas-Kanade flow from one frame to the next. Points whose motion is far from the median are dropped.
4. **Move the box** by that median motion. The centroid is the centre of the box.
5. **Correct with the detector** every 15 frames, and also if the flow has too few points. I keep the detection when it overlaps the flow box (IoU ≥ 0.3).
6. **Bearing:** the box centre is turned into a line of sight with the camera matrix, (u − cx) / fx and (v − cy) / fy. That angle from the boresight is stored with each frame.

Over 300 frames, 280 updates came from flow and 19 from the detector (plus the first frame). Flow never fully failed. The centroid moved from about (916, 468) to (682, 583), about 1210 px in total. The angle from the optical axis went from about 6.8° to 1.9°.

## Pictures and files

- `src/track_sequence.py` — the tracker
- `results/tracking_examples/track.json` — box, centroid, bearing, and whether the update was flow or the detector
- `results/tracking_examples/summary.json` — the 300-frame totals
- `results/tracking_examples/trajectory.png` — centroid path
- `results/tracking_examples/tracking_montage.png`
- `results/tracking_examples/track_0001.jpg`, `track_0150.jpg`, `track_0300.jpg`

Running `src/track_sequence.py` again writes a new set under `results/tracking/`. The figures packed here are the ones in `results/tracking_examples/`.

The sampled frames keep the box on the spacecraft while it tumbles. The centroid plot is jagged because the detector pulls the box back every 15 frames.

## Where this track fails

1. **Glints and shadow.** Corners stick to a bright panel. The panel moves differently from the body, so the box drifts until the next detection.
2. **Earth or stars near the box.** Those points are not on the spacecraft. The median gate removes some of them. A bright Earth edge can still shift the flow.
3. **The target changes shape.** Rotation, or a face going into shadow, drops the matched points. The detector is there to restart the box. If the detector also misses, the last box is kept.
4. **Size change.** Flow only shifts the box. The width and height change when the detector is fused in, not from the features themselves.

The sequence has no ground truth, so I cannot quote an IoU for the track. The check is the drawn frames and how often the detector had to step in.
