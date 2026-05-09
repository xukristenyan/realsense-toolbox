"""Live view from a RealSense camera, no recording. ESC to quit."""
import time

from realsense_toolbox import (
    Camera, CameraConfig, RealSenseConfig, ViewerConfig, KeyListener,
)


def main():
    serial = "244622072715"
    cfg = CameraConfig(
        realsense=RealSenseConfig(streams=["color", "depth"]),
        viewer=ViewerConfig(show=["color", "depth"]),
    )
    cam = Camera(serial, cfg)

    print("Press ESC to quit.")
    cam.launch()
    try:
        with KeyListener() as keys:
            while cam.is_alive:
                cam.get_observations()
                if keys.consume_pressed("esc"):
                    break
                time.sleep(0.01)
    finally:
        cam.shutdown()


if __name__ == "__main__":
    main()
