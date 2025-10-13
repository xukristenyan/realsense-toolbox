from .camera import Camera
from .utils import start_keypress, end_keypress


class CameraSystem:
    '''
    To easily manage multiple Camera objects in an environment.
    '''
    def __init__(self, system_config: dict):
        self.cameras = {}

        self.auto_start = True
        self.recording_started = False

        for serial, config in system_config.items():
            self.cameras[serial] = Camera(serial, config)

            if config.get("enable_recorder", False) and not config.get("recorder", {}).get("auto_start", True):
                self.auto_start = False


    def launch(self):
        for serial, camera in self.cameras.items():
            camera.launch()
        self.is_alive = True

        print("[System] All cameras launched!")


    def update(self, overlays_by_serial=None):
        if overlays_by_serial is None:
            overlays_by_serial = {}
            
        all_frames = {}

        if not self.auto_start:
            if not self.recording_started and start_keypress():
                self.recording_started = True
                for serial, camera in self.cameras.items():
                    camera.control_recording(True)

            if self.recording_started and end_keypress():
                self.recording_started = False
                for serial, camera in self.cameras.items():
                    camera.control_recording(False)

        for serial, camera in self.cameras.items():
            camera_overlays = overlays_by_serial.get(serial, None)

            camera.update(overlays=camera_overlays)

            if not camera.is_alive:
                self.is_alive = False

            color, depth, color_frame, depth_frame = camera.get_current_state()
            if color is not None and depth is not None:
                all_frames[serial] = (color, depth, color_frame, depth_frame)
        
        return all_frames


    def shutdown(self):
        for camera in self.cameras.values():
            camera.shutdown()

        print("[System] Shutdown complete.")