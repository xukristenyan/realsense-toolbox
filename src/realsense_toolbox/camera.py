import time
from .realsense import RealSenseCamera
from .viewer import Viewer
from .recorder import Recorder
from .utils import start_keypress, end_keypress


class Camera:
    '''
    A high-level container for a single RealSense device managing its core camera stream, viewer, and recorder components.
    '''
    def __init__(self, serial, config):
        self.serial = serial

        rs_config = config.get("specifications", {})
        self.rs_camera = RealSenseCamera(self.serial, rs_config)

        if config.get("enable_viewer", True):
            conf = config.get("viewer", {})
            viewer_config = {
                "show_color": conf.get("show_color", True),
                "show_depth": conf.get("show_depth", False),
                "fps": conf.get("fps", 30)
            }
            self.viewer = Viewer(self.serial, viewer_config)
        else:
            self.viewer = None

        if config.get("enable_recorder", False):
            conf = config.get("recorder", {})
            save_time = time.strftime("%Y%m%d_%H%M%S")
            recorder_config = {
                "save_dir": conf.get("save_dir", "./recordings"),
                "save_name": conf.get("save_name", f"{save_time}"),
                "fps": conf.get("fps", 10),
                "save_with_overlays": conf.get("save_with_overlays", False),
            }
            self.recorder = Recorder(self.serial, recorder_config)
            self.auto_start = conf.get("auto_start", True)
        else:
            self.recorder = None

        self.is_alive = False
        self.recording_started = False

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
                if not self.auto_start:
                    if not self.recording_started and start_keypress():
                        self.recording_started = True
                        print(f"[Recorder] Recording started !!!")

                    if self.recording_started and end_keypress():
                        self.recording_started = False
                        print(f"[Recorder] Recording stopped !!!")

                else:
                    if not self.recording_started:
                        self.recording_started = True
                        print(f"[Recorder] Recording started !!!")

                if self.recording_started:
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
