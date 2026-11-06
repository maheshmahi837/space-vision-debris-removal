# Bonus II: System architecture and validation

Camera B feeds the Task 3 detector and the Bonus I tracker. A navigation filter and GNC would use those measurements. I did not code the filter or the GNC.

Camera B cannot see a 0.5 m target at 1 km (about 0.7 pixel). Beyond about 250 m the chaser needs a navigation prior or a second, narrower camera. After that, one Camera B is enough.

## Block diagram

```text
Camera B (2048x2048, 8 mm, 70 deg, 1.8 W)
    -> ISP (exposure; no distortion model was given)
        -> Detector: one box + score, at the start and about every 15 frames
        -> Tracker: corners + optical flow inside the box, every frame
            -> box centre and line of sight, with a valid/coast flag
                -> Navigation filter (bearing, rough range)
                    -> GNC at 5 Hz or faster
```

The centroid is the centre of the box, (x + w/2, y + h/2).

## Interfaces and timing

GNC needs an update every 200 ms. Below 10 m the camera must run at 10 fps or more.

| From | To | What | Rate | Budget |
|---|---|---|---|---|
| Camera | ISP | Frame and its time | 5 fps far out, ≥ 10 fps below 10 m | ~50 ms |
| Detector | Tracker | One box and a score | start, after a loss, every ~15 frames | < 100 ms |
| Tracker | Filter | Box, centre, flow or coast | every frame | < 20 ms |
| Filter | GNC | Bearing, rough range, coast flag | ≥ 5 Hz | < 20 ms |

50 + 100 + 20 ms is about 170 ms, inside the 200 ms cycle. Flow runs every frame. The detector is only used to start the box and to fix it.

On Camera B the filter can claim a bearing from about 240 m (3 pixels), and pose from about 15 m (50 pixels). At 1 km it should not claim a detection.

## How I would check it

| Check | How |
|---|---|
| Already done | IoU, detection rate, and centroid error on 120 validation images (94% at IoU ≥ 0.5, 13 px median error). Track looked at on 300 frames. Test boxes are in `test_predictions.json`. |
| Simulation | Approach from 250 m to 1 m with sun, shadow, 2 deg/s rotation, ±2 deg pointing, and Earth in view. Compare the filter with the simulator truth. |
| Hardware-in-the-loop | Camera B looking at a known satellite model. Measure timing error, dropouts, and centroid error in pixels. |
| Flight-like cases | Handover from the long-range cue, eclipse, glint, Earth behind the target, and losing the track inside 10 m. Pass if the track comes back in a few seconds and the chaser slows down while the flag says coast. |

## Risks

1. **1 km.** Under one pixel, so a search there false-alarms. Hand over from a prior or a narrow camera inside about 250 m.
2. **Glint and Earth.** The box centre sticks to a bright panel or to clutter. Drop the measurement when the score or the corner count falls.
3. **Slow detector on the spacecraft.** Flow every frame, detector only to start or recover, so the 200 ms deadline still holds.
4. **Range from the box.** R ≈ 0.5 / θ is only a rough range until the target is about 50 pixels across. If the track drops for more than one or two GNC cycles close in, slow down.
