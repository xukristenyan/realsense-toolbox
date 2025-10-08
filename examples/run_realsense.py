import time
from realsense_toolbox import RealSenseCamera
from realsense_toolbox.utils import quit_keypress

def main():
    # ===== YOUR CHANGES =====
    serial = "YOUR SERIAL"

    # see readme for full configurations.
    specs = {
            "fps": 30,
            "color_auto_exposure": False,
            "depth_auto_exposure": False,
        }

    # ========================

    camera = None
    try:
        camera = RealSenseCamera(serial, specs)
        camera.launch()
        
        while True:
            color_image, depth_image = camera.get_images()

            if color_image is None or depth_image is None:
                time.sleep(0.01)
                continue
            
            if quit_keypress():
                break

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting gracefully.")

    except Exception as e:
        print(f"Unexpected error occurred: {e}")

    finally:
        if camera:
            camera.shutdown()



if __name__ == "__main__":
    main()