"""
Record IR-stereo + color for offline Fast-FoundationStereo replay.

Output (per session): cam_<last3>_color.mp4 + cam_<last3>_color.npz +
cam_<last3>_left_ir.npz + cam_<last3>_right_ir.npz + calibration.json.
The .npz pair plus calibration.json is everything FFS needs to re-infer
depth offline; color is preserved losslessly for downstream cv operations.

Press 's' to start, 'e' to stop, ESC to quit.
"""
import time

from realsense_toolbox import (
    Camera, CameraConfig, RealSenseConfig, RecorderConfig, KeyListener,
)


def main():
    serial = "244622072715"
    cfg = CameraConfig(
        realsense=RealSenseConfig(
            streams=["color", "ir_stereo"],
            ir_emitter=False,           # off so projector dots don't pollute IR pair
        ),
        recorder=RecorderConfig(
            streams=["color", "ir_stereo"],   # ir_stereo also triggers color.npz + calibration.json
            save_name="ffs_trial",
            fps=10,
        ),
    )
    cam = Camera(serial, cfg)

    print("Press 's' to start recording, 'e' to stop, ESC to quit.")
    cam.launch()

    try:
        with KeyListener() as keys:
            while cam.is_alive:
                cam.get_observations()
                if keys.consume_pressed("s"):
                    cam.start_recording()
                if keys.consume_pressed("e"):
                    cam.stop_recording()
                if keys.consume_pressed("esc"):
                    break
                time.sleep(0.01)

    finally:
        cam.shutdown()


if __name__ == "__main__":
    main()
