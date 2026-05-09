"""
Smoke test for Camera + Recorder over SSH (no viewer).

Mode B (color + ir_stereo): exercises all recording branches:
 - color.mp4 (always)
 - color.npz (because ir_stereo is also recorded)
 - left_ir.npz, right_ir.npz
 - cam_<last3>_calibration.json
"""
import json
import time
from pathlib import Path

from realsense_toolbox.camera import Camera
from realsense_toolbox.config import CameraConfig, RealSenseConfig, RecorderConfig

SERIAL = "244622072715"
DURATION_S = 3
SAVE_NAME = "smoke_camera_test"


def main():
    cfg = CameraConfig(
        realsense=RealSenseConfig(streams=["color", "ir_stereo"], ir_emitter=False),
        viewer=None,
        recorder=RecorderConfig(
            streams=["color", "ir_stereo"], save_name=SAVE_NAME, fps=10),
    )
    cam = Camera(SERIAL, cfg)

    try:
        cam.launch()
        assert cam.is_alive
        print(f"is_alive: {cam.is_alive}")

        # Wait for first frame
        for _ in range(100):
            obs = cam.get_observations()
            if obs:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("No observations within 5s")
        print(f"first obs streams: {sorted(obs.keys())}")

        # Record
        cam.start_recording()
        end_t = time.time() + DURATION_S
        ticks = 0
        while time.time() < end_t:
            cam.get_observations()
            ticks += 1
            time.sleep(0.02)
        cam.stop_recording()
        print(f"ticks during {DURATION_S}s recording: {ticks}")
    finally:
        cam.shutdown()

    # Verify outputs
    sess = Path("./recordings") / SAVE_NAME
    print(f"\nSession dir: {sess.resolve()}")
    assert sess.exists(), f"session dir not created: {sess}"

    last3 = SERIAL[-3:]
    expected = [
        f"cam_{last3}_color.mp4",
        f"cam_{last3}_color.npz",
        f"cam_{last3}_left_ir.npz",
        f"cam_{last3}_right_ir.npz",
        f"cam_{last3}_calibration.json",
    ]
    for fname in expected:
        p = sess / fname
        assert p.exists(), f"missing: {p}"
        print(f"  {fname}: {p.stat().st_size:,} bytes")

    # Calibration sanity
    calib = json.loads((sess / f"cam_{last3}_calibration.json").read_text())
    print(f"\ncalibration.json keys: {sorted(calib.keys())}")
    assert "K_canonical" in calib
    assert "K_ir" in calib
    assert "baseline" in calib
    assert "ir_to_color_R" in calib
    assert "ir_to_color_t" in calib
    print(f"baseline: {calib['baseline']:.6f} m")
    print(f"ir_to_color t: {calib['ir_to_color_t']}")
    print(f"ir_emitter: {calib.get('ir_emitter')}, "
          f"camera_fps: {calib.get('camera_fps')}, recorder_fps: {calib.get('recorder_fps')}")

    # NPZ sanity
    import numpy as np
    color_arr = np.load(sess / f"cam_{last3}_color.npz")["frames"]
    left_arr = np.load(sess / f"cam_{last3}_left_ir.npz")["frames"]
    right_arr = np.load(sess / f"cam_{last3}_right_ir.npz")["frames"]
    print(f"\ncolor frames: shape={color_arr.shape}, dtype={color_arr.dtype}")
    print(f"left_ir frames: shape={left_arr.shape}, dtype={left_arr.dtype}")
    print(f"right_ir frames: shape={right_arr.shape}, dtype={right_arr.dtype}")
    assert color_arr.shape[0] == left_arr.shape[0] == right_arr.shape[0], \
        "frame counts should match across streams"

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
