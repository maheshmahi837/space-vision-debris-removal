# Task 1: Mission requirements and vision sensor analysis

A servicing spacecraft approaches a dead satellite in low Earth orbit, about 450 km altitude. The target is about 0.5 m across, sends no navigation data, and may rotate at up to 2 deg/s. The camera has to watch it from 1 km down to 1 m. Approach speed is at most 0.1 m/s, and 0.01 m/s below 5 m. Pointing is about ±2 deg. GNC needs a new relative-navigation update at 5 Hz or faster (every 200 ms).

I assume one camera and a pinhole model. The centroid I use is the centre of the bounding box, (x + w/2, y + h/2). For a rough range I assume the target size is 0.5 m. Same pixel rules as Task 2: 3 pixels across the target to detect it, 50 pixels before pose.

## Measurements along the approach

- **Far (around 1 km to 100 m):** is the target in the frame, and where is the box centre. That centre is the line of sight.
- **Middle (around 100 m to 10 m):** bounding box and its centre. Box size gives a rough range, R ≈ 0.5 / θ. This is only a rough range, because the box can be loose.
- **Close (around 10 m to 1 m):** the same centre, tracked faster, plus features for attitude once the target is about 50 pixels across.

One camera frame does not give a true 3D position unless the size is assumed, and it does not give attitude while the target is only a few pixels wide.

## Requirements

Functional:

1. Detect the one target spacecraft.
2. Output a bounding box, the box-centre centroid, and a confidence.
3. Turn the centroid into a bearing for GNC.
4. Keep the track as the target rotates and grows, and support pose once it is large enough.

Performance:

1. At least 5 Hz, with the whole vision step finished inside 200 ms.
2. Keep the target in the field of view with ±2 deg pointing error.
3. At least 3 pixels across the target at 1 km, if we must detect it there.
4. About 50 pixels across the target before pose.
5. Work in sun, shadow, and with Earth in the background, and with rotation up to 2 deg/s.

## Camera numbers

Angular size θ ≈ L / R, with L = 0.5 m.

| Range | Angular size |
|---|---|
| 1 km | 0.50 mrad (0.029 deg) |
| 100 m | 5.0 mrad (0.29 deg) |
| 10 m | 50 mrad (2.9 deg) |
| 1 m | 500 mrad (29 deg) |

Pixels across the target: N = θ / IFOV, and IFOV = pixel size / focal length.

- 3 pixels at 1 km needs IFOV ≤ 0.5 / (1000 × 3) = **0.17 mrad/pixel**.
- 50 pixels at 50 m needs IFOV ≤ 0.5 / (50 × 50) = **0.20 mrad/pixel**.

Field of view has to cover the pointing error as well as the target. I add ±2 deg pointing and 1 deg of margin.

| Range | Full FOV I would want |
|---|---|
| 1 km | about 6 deg |
| 10 m | about 9 deg |
| 1 m | about 35 deg |

At 1 km the target is tiny, so the field of view is easy. At 1 m the target itself is about 29 deg across, so a narrow lens cuts it off. If there is only one camera, I would size the field of view for the close range.

In one 200 ms cycle the chaser moves 2 cm at 0.1 m/s (0.2 cm at 0.01 m/s), and the target can rotate 0.4 deg. A fixed template will go stale. Processing also needs automatic exposure, because panels saturate while the body stays dark.

For one fixed lens I would ask for:

- IFOV of about 0.17 mrad/pixel or finer, if detection at 1 km is required
- full FOV of about 35 deg, if the same camera must still see the target at 1 m
- at least 5 fps, with processing under 200 ms

A long focal length gives the fine pixel scale and a small field of view. Those two requirements do not fit on one lens. That is the choice in Task 2.

## Operational challenges

1. **Lighting.** Panels saturate and the body can be almost black. The bright spot moves as the target rotates. A brightness threshold locks onto the glint, so the box centre, and the bearing sent to GNC, shifts off the middle of the spacecraft.

2. **Earth and stars.** The target is sometimes in front of Earth, not black sky. Stars are small and bright. Finding the brightest blob then tracks clutter, and GNC steers on a false target.

3. **Size change and rotation.** From 1 km to 1 m the target grows by about 1000 times in angle, and it can rotate at 2 deg/s, so the outline keeps changing. A detector with one scale, or a tracker stuck on the first patch, loses it. The track has to be restarted when the appearance changes.
