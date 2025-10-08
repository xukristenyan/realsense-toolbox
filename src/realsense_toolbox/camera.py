import time
from .realsense import RealSenseCamera
from .viewer import Viewer
from .recorder import Recorder


class Camera:
    '''
    A high-level container for a single RealSense device managing its core camera stream, viewer, and recorder components.
    '''
    def __init__(self, serial, config: dict):
        self.serial = serial

        rs_config = config.get("specifications", {})
        self.rs_camera = RealSenseCamera(self.serial, rs_config)

        if config.get("enable_viewer"):
            conf = config.get("viewer", {})
            viewer_config = {
                "show_color": conf.get("show_color", True),
                "show_depth": conf.get("show_depth", False),
                "fps": conf.get("fps", 30)
            }
            self.viewer = Viewer(self.serial, viewer_config)
        else:
            self.viewer = None

        if config.get("enable_recorder"):
            conf = config.get("recorder", {})
            save_time = time.strftime("%Y%m%d_%H%M%S")
            recorder_config = {
                "save_dir": conf.get("save_dir", "./recordings"),
                "save_name": conf.get("save_name", f"{save_time}"),
                "fps": conf.get("fps", 10),
                "save_with_overlays": conf.get("save_with_overlays", False)
            }
            self.recorder = Recorder(self.serial, recorder_config)
        else:
            self.recorder = None

        self.is_alive = False


    def launch(self):
        self.rs_camera.launch()
        self.is_alive = True


    def update(self, overlays=None):
        '''
        Fetches the latest frames and updates the viewer and recorder.
        This is meant to be called from an external loop.
        '''
        color_image, depth_image, color_frame, depth_frame = self.rs_camera.get_current_state()

        if color_image is not None and depth_image is not None:

            if self.recorder:
                self.recorder.update(color_image, depth_image, overlays)
            
            if self.viewer:
                self.viewer.update(color_image, depth_image, overlays)
                if not self.viewer.viewer_alive:
                    self.is_alive = False

        return color_image, depth_image, color_frame, depth_frame


    def shutdown(self):
        if self.recorder:
            self.recorder.stop()
        self.rs_camera.shutdown()