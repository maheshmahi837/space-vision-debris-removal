# Task 2: Camera performance trade-off

Pick one camera for a 0.5 m object, from 1 km down to 1 m.

Constraints: power ≤ 3 W, at least 10 fps below 10 m, at least 3 pixels across the target to detect it, at least 50 pixels for pose.

I use a pinhole camera. IFOV = p / f. Pixels across the target N = (0.5 / R) / IFOV. Full FOV = 2 arctan(pixel count × p / (2 f)). No distortion is given, so I ignore it.

## Cameras

| | Camera A | Camera B |
|---|---|---|
| Resolution | 4512 × 4512 | 2048 × 2048 |
| Pixel size | 2.74 µm | 5.5 µm |
| Focal length | 35 mm | 8 mm |
| Max frame rate | 18 fps | 60 fps |
| Read noise | 2.3 e− | 6.0 e− |
| Power | 3.2 W | 1.8 W |
| IFOV = p / f | 0.078 mrad/pixel | 0.69 mrad/pixel |
| Full FOV | 20 deg | 70 deg |

A is about 9 times finer in angle. B's pixels are about 4 times the area (7.5 µm² vs 30 µm²), so each pixel collects more light if the same illumination hits the sensor. I cannot turn that into a real SNR: f-number, quantum efficiency and exposure time are not given.

## Pixels on target

| Range | Camera A | Camera B | Detect (≥ 3 px) | Pose (≥ 50 px) |
|---|---|---|---|---|
| 1 km | 6.4 | 0.7 | A only | no |
| 100 m | 64 | 7 | both | A only |
| 15 m | 440 | 50 | both | both |
| 1 m | larger than the 20 deg frame | 730 | both | both |

- A reaches 3 pixels out to about 2.1 km, and 50 pixels from about 130 m.
- B reaches 3 pixels from about 240 m, and 50 pixels from about 15 m.

A can detect at 1 km. B is still under 1 pixel there, so I would not call that a detection. At 1 m, A cuts the target off: the spacecraft is about 29 deg across and the lens is only 20 deg. B's 70 deg field still contains it, even with ±2 deg pointing error.

## Constraints

| Check | A | B |
|---|---|---|
| Power ≤ 3 W | No (3.2 W) | Yes (1.8 W) |
| ≥ 10 fps below 10 m | Yes (18 fps) | Yes (60 fps) |
| Detect at 1 km | Yes | No |
| Pose | from ~130 m | from ~15 m |
| See the whole target at 1 m | No | Yes |

Both are fast enough below 10 m. B has more spare frames. A is 0.2 W over the power cap.

On sensitivity, A has lower read noise, which helps a faint few-pixel target. B gathers more light per pixel, but at 1 km the target is still smaller than one pixel, so the extra light does not make it resolved.

## Trade-off

A is the long-range camera: detection at 1 km and pose from about 130 m, with lower read noise. It fails the 3 W limit and its 20 deg field of view clips the target near 1 m.

B is the close-range camera: inside the power limit, 70 deg field of view, 60 fps. It only detects from about 240 m, and only supports pose from about 15 m.

## Missing information

Before a flight choice I would still want: f-number and stray-light performance, quantum efficiency and dark current, whether the power numbers are peak or average, mass and heater power, and whether a second camera is allowed. "3 pixels" on black sky is also easier than "3 pixels" against the Earth.

## Choice

I pick **Camera B**.

A fails the power limit, and it cannot keep the whole target in frame at 1 m. B meets power, frame rate and the close-range field of view, which is where a bad bearing is most dangerous. It does not detect at 1 km (about 0.7 pixel). Acquisition that far has to come from a navigation prior or a second, narrower camera, with handover to B inside about 250 m.
