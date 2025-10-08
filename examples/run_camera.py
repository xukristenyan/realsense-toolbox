'''
In this example, it launches a realsense camera with live view of the streaming and recording.
'''
import time
from realsense_toolbox.camera import Camera

def main():

    # ===== YOUR CHANGES =====
    serial = "YOUR SERIAL"

    # see readme for full configurations.
    camera_config = {
        "enable_viewer": True,
        "enable_recorder": True,

        "specifications": {
            "fps": 30,
        "color_auto_exposure": False,
        "depth_auto_exposure": False,
        },

        "viewer": {                     # no need to keep this dict if "enable_viewer" is False
            "show_color": True,
            "show_depth": True,
            "fps": 10
        },

        "recorder": {                   # no need to keep this dict if "enable_recorder" is False
            "save_dir": "./recordings",
            "save_name": "my_third_session",
            "fps": 10,
            "save_with_overlays": True
        }
    }
    # ========================


    camera = None
    try:
        camera = Camera(serial, camera_config)
        camera.launch()

        while True:

            # ===== YOUR CHANGES =====
            # mimic overlays to be added
            moving_x = int(100 + 50 * (1 + time.time() % 4))
            
            # see readme for full configurations.
            overlays = [
                {
                    "type": "dot",
                    "xy": (moving_x, 200),
                    # "radius": 8,
                    # "color": (0, 255, 0) # Green
                }
            ]
            # ========================

            camera.update(overlays=overlays)

            if not camera.is_alive:
                break

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting gracefully.")

    except Exception as e:
        print(f"Unexpected error occurred: {e}")

    finally:
        if camera:
            camera.shutdown()

        print("Shutdown complete!")



if __name__ == "__main__":
    main()