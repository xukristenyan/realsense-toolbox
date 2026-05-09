"""
Two RealSense cameras with synchronized start/stop recording.

Press 's' to start recording on all cameras, 'e' to stop, ESC to quit.
"""
import time

from realsense_toolbox import (
    CameraSystem, CameraConfig, RealSenseConfig, ViewerConfig, RecorderConfig,
    KeyListener,
)


def main():
    serial_a = "244622072715"
    serial_b = "244622072716"   # update to your second camera's serial

    common_rs = RealSenseConfig(streams=["color", "depth"])
    common_rec = lambda: RecorderConfig(streams=["color", "depth"], save_name="trial")

    configs = {
        serial_a: CameraConfig(
            realsense=common_rs,
            viewer=ViewerConfig(show=["color"]),
            recorder=common_rec(),
        ),
        serial_b: CameraConfig(
            realsense=common_rs,
            viewer=ViewerConfig(show=["color"]),
            recorder=common_rec(),
        ),
    }

    system = CameraSystem(configs)

    print("Press 's' to start recording (all cams), 'e' to stop, ESC to quit.")
    system.launch()

    try:
        with KeyListener() as keys:
            while system.is_alive:
                system.get_observations()
                if keys.consume_pressed("s"):
                    system.start_recording()
                if keys.consume_pressed("e"):
                    system.stop_recording()
                if keys.consume_pressed("esc"):
                    break
                time.sleep(0.01)

    finally:
        system.shutdown()


if __name__ == "__main__":
    main()
