"""
Headless recording from a RealSense camera (no viewer).

Press 's' to start, 'e' to stop, ESC to quit.
"""
import time

from realsense_toolbox import (
    Camera, CameraConfig, RealSenseConfig, RecorderConfig, KeyListener,
)


def main():
    serial = "244622072715"
    cfg = CameraConfig(
        realsense=RealSenseConfig(streams=["color", "depth"]),
        recorder=RecorderConfig(
            streams=["color", "depth"],
            save_name="trial",
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
