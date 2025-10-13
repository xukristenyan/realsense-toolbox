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

        self.color_image = None 
        self.depth_image = None 
        self.color_frame = None 
        self.depth_frame = None


    def launch(self):
        self.rs_camera.launch()
        self.is_alive = True


    def update(self, overlays=None):
        '''
        Fetches the latest frames and updates the viewer and recorder.
        This is meant to be called from an external loop.
        '''
        self.color_image, self.depth_image, self.color_frame, self.depth_frame = self.rs_camera.get_current_state()

        if self.color_image is not None and self.depth_image is not None:

            if self.recorder:
                if not self.recording_started:
                    if self.auto_start:
                        self.recording_started = True
                        print(f"[Recorder] {self.serial[-3:]} Recording started !!!")

                    elif start_keypress():
                        self.recording_started = True
                        print(f"[Recorder] {self.serial[-3:]} Recording started !!!")

                if self.recording_started:
                    self.recorder.update(self.color_image, self.depth_image, overlays)

                    if end_keypress():
                        self.recording_started = False
                        print(f"[Recorder] {self.serial[-3:]} Recording stopped !!!")

            if self.viewer:
                self.viewer.update(self.color_image, self.depth_image, overlays)
                if not self.viewer.viewer_alive:
                    self.is_alive = False


    def get_current_state(self):
        return self.color_image, self.depth_image, self.color_frame, self.depth_frame


    def get_images(self):
        return self.rs_camera.get_images()


    def shutdown(self):
        if self.recorder:
            self.recorder.stop()
        self.rs_camera.shutdown()


    def control_recording(self, start):
        self.recording_started = start