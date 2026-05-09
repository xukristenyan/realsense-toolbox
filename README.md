# RealSense Toolbox

A small Python toolbox for streaming, viewing, and recording from Intel RealSense D4xx cameras. Built around composable, typed configs; supports synchronized multi-camera setups and Fast-FoundationStereo-replay-friendly recording (lossless IR pair + calibration).

## Installation

Requires Python 3.10. The RealSense SDK (`pyrealsense2`) is a dependency.

```bash
git clone https://github.com/xukristenyan/realsense-toolbox.git
cd realsense-toolbox
uv sync
```

Or to use as an editable dependency in another project:

```bash
# uv
uv add --editable /path/to/realsense-toolbox

# pip
pip install -e /path/to/realsense-toolbox
```

## Quick start

```python
from realsense_toolbox import (
    Camera, CameraConfig, RealSenseConfig, ViewerConfig, KeyListener,
)

cam = Camera("244622072715", CameraConfig(
    realsense=RealSenseConfig(streams=["color", "depth"]),
    viewer=ViewerConfig(show=["color", "depth"]),
))

cam.launch()
try:
    with KeyListener() as keys:
        while cam.is_alive:
            cam.get_observations()
            if keys.consume_pressed("esc"):
                break
finally:
    cam.shutdown()
```

More patterns in `examples/`.

## Architecture

| Class | Role |
|---|---|
| `RealSenseCamera` | Direct `pyrealsense2` wrapper. Captures frames in a background thread; exposes them as numpy arrays via `get_current_state()`. |
| `Viewer` | Display sink. Accepts a streams dict and renders selected streams side-by-side in one OpenCV window. |
| `Recorder` | File sink. Accepts a streams dict; writes per-stream files (mp4 or npz) plus calibration when applicable. |
| `Camera` | Single-camera orchestrator. Composes `RealSenseCamera` + optional `Viewer` + optional `Recorder`. Exposes `get_observations()`, `start_recording()`, `stop_recording()`. |
| `CameraSystem` | Multi-camera coordinator. Broadcasts the same orchestration across N cameras. |
| `KeyListener` | Terminal-stdin keyboard reader (utils). Edge-triggered; consume each press once. |

The orchestrator is a pure facade — no keyboard polling, no auto-recording. The caller drives the loop.

## Configuration

Four dataclasses. Each accepts a dict alternative (the constructor normalizes dicts → dataclasses).

### `RealSenseConfig` — camera capture

```python
@dataclass
class RealSenseConfig:
    streams: list[str] = ["color", "depth"]      # subset of {"color", "depth", "ir_stereo"}
    fps: int = 30
    width: int = 640
    height: int = 480
    color_auto_exposure: bool = True
    depth_auto_exposure: bool = True
    ir_emitter: bool | None = None               # None = auto: True iff "depth" in streams
```

Stream IDs:
- `"color"` — RGB (BGR8). Acts as the alignment target when `"depth"` is also enabled.
- `"depth"` — on-device depth (Z16), aligned to color when `"color"` is enabled.
- `"ir_stereo"` — left + right IR pair (Y8). For external stereo (e.g. Fast-FoundationStereo).

### `ViewerConfig` — display window

```python
@dataclass
class ViewerConfig:
    show: list[str] = ["color"]                  # subset of {"color", "depth", "left_ir", "right_ir"}
    fps: int = 30                                # display rate cap
```

### `RecorderConfig` — file output

```python
@dataclass
class RecorderConfig:
    streams: list[str] = ["color"]               # subset of {"color", "depth", "ir_stereo"}
    save_dir: str = "./recordings"
    save_name: str | None = None                 # None = auto-timestamp at start()
    fps: int = 10                                # frames sampled per second (decoupled from camera fps)
    save_with_overlays: bool = False
```

### `CameraConfig` — top-level

```python
@dataclass
class CameraConfig:
    realsense: RealSenseConfig | dict = RealSenseConfig()
    viewer:    ViewerConfig | dict | None = None        # None disables the viewer
    recorder:  RecorderConfig | dict | None = None      # None disables the recorder
```

## Examples

| File | Use case |
|---|---|
| `examples/stream_only.py` | Direct `RealSenseCamera`. Saves N frames; SSH-friendly. |
| `examples/view_live.py` | `Camera` + `Viewer`. Live display; ESC to quit. |
| `examples/record_headless.py` | `Camera` + `Recorder`. KeyListener-driven start/stop; no viewer. |
| `examples/view_and_record.py` | All three. Live display + on-demand recording. |
| `examples/record_for_ffs.py` | IR-stereo capture for offline FoundationStereo replay. |
| `examples/multi_camera.py` | `CameraSystem` with synchronized recording across two cameras. |

Run any of them with `uv run examples/<name>.py`.

## Recording outputs

Files saved under `{save_dir}/{save_name}/`. Names always carry a `cam_<last3-of-serial>_` prefix so multiple cameras don't collide.

| File | Created when |
|---|---|
| `cam_<last3>_color.mp4` | `"color"` in streams (lossy h264, ~5 MB/min @ 10 fps) |
| `cam_<last3>_color.npz` | `"color"` AND `"ir_stereo"` in streams (lossless uint8, ~80 MB/min @ 10 fps) |
| `cam_<last3>_depth.mp4` | `"depth"` in streams (lossy colormap, visual review only) |
| `cam_<last3>_left_ir.npz` | `"ir_stereo"` in streams (lossless uint8) |
| `cam_<last3>_right_ir.npz` | `"ir_stereo"` in streams (lossless uint8) |
| `cam_<last3>_overlay.mp4` | `save_with_overlays=True` and `"color"` in streams |
| `cam_<last3>_calibration.json` | `"ir_stereo"` in streams |

### Why color gets two formats in IR-stereo mode

Recording IR stereo signals an intent to preserve data for offline use (FFS replay, SAM2 on color, photometric analysis, etc.). The Recorder upgrades color to bit-exact `.npz` while still writing `.mp4` for quick visual review. ~10× larger than mp4-only, but no compression artifacts.

### `cam_<last3>_calibration.json` fields

```json
{
    "K_canonical": [[fx, 0, ppx], [0, fy, ppy], [0, 0, 1]],
    "K_ir":        [[fx, 0, ppx], [0, fy, ppy], [0, 0, 1]],
    "baseline": 0.050036,
    "depth_scale": 0.001,
    "ir_to_color_R": [[...]],
    "ir_to_color_t": [tx, ty, tz],
    "streams": ["color", "ir_stereo"],
    "ir_emitter": false,
    "camera_fps": 30,
    "recorder_fps": 10,
    "width": 640,
    "height": 480
}
```

`K_canonical` is whichever stream the camera reports first by priority `color > ir_stereo > depth`. `K_ir` and the IR↔color extrinsics are present whenever IR stereo is enabled.

## Offline Fast-FoundationStereo replay

After recording with `streams=["color", "ir_stereo"]`, the saved files are self-contained for offline depth re-inference:

```python
import numpy as np, json
from your_ffs_client import FFSClient

session = "recordings/ffs_trial"
calib = json.load(open(f"{session}/cam_715_calibration.json"))
left  = np.load(f"{session}/cam_715_left_ir.npz")["frames"]
right = np.load(f"{session}/cam_715_right_ir.npz")["frames"]

client = FFSClient()
client.set_intrinsics(np.array(calib["K_ir"]), calib["baseline"])

for i in range(len(left)):
    out = client.infer(left[i], right[i], returns=("depth",))
    depth = out["depth"]
    # ...
```

The IR images are bit-exact to capture, so the result is identical to running FFS live during recording.

## Overlays

`Camera.get_observations(overlays=...)` and `Viewer.update`/`Recorder.update` accept an optional list of overlay dicts. Overlays are drawn on the **color** panel only.

```python
overlays = [
    {"type": "dot",  "xy": (320, 240), "radius": 6, "color": (0, 255, 0)},
    {"type": "text", "content": "trial_42", "position": (50, 50), "color": (0, 0, 255)},
]
cam.get_observations(overlays=overlays)
```

## Notes

- **IR projector & FFS.** The dot pattern can degrade neural-net stereo output on textured scenes. `record_for_ffs.py` defaults to `ir_emitter=False`. Test both on your specific scenes.
- **Memory cost during recording.** npz streams (color+IR in FFS mode) are buffered in RAM until `stop_recording()` flushes them. Roughly 250–500 MB per minute for an IR pair at 10 fps. Long sessions can pressure RAM — split into multiple shorter recordings if needed.
