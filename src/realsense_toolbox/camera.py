from .config import CameraConfig
from .realsense import RealSenseCamera
from .viewer import Viewer
from .recorder import Recorder


class Camera:
    """
    High-level facade: RealSenseCamera + optional Viewer + optional Recorder.

    Pure orchestration — no keyboard input, no recording auto-trigger. The
    caller (or CameraSystem) decides when to start/stop recording.

    Typical use:
        cam = Camera(serial, CameraConfig(
            realsense=RealSenseConfig(streams=["color", "depth"]),
            viewer=ViewerConfig(show=["color"]),
        ))
        cam.launch()
        while cam.is_alive:
            streams = cam.get_observations(overlays=...)
        cam.shutdown()
    """

    def __init__(self, serial, config=None):
        self.serial = serial

        if config is None:
            config = CameraConfig()
        elif isinstance(config, dict):
            config = CameraConfig(**config)
        self.cfg = config

        self.rs_camera = RealSenseCamera(serial, self.cfg.realsense)
        self.viewer = Viewer(serial, self.cfg.viewer) if self.cfg.viewer is not None else None
        self.recorder = Recorder(serial, self.cfg.recorder) if self.cfg.recorder is not None else None

        self._is_alive = False


    def launch(self):
        self.rs_camera.launch()
        self._is_alive = True


    def get_observations(self, overlays=None):
        """Return the latest stream snapshot from the camera and, as a side
        effect, push it to the viewer and recorder if they're enabled.

        Call this once per loop iteration. Returns the streams dict
        (matching RealSenseCamera.get_current_state()).
        """
        streams = self.rs_camera.get_current_state()
        if self.viewer is not None:
            self.viewer.update(streams, overlays=overlays)
        if self.recorder is not None:
            self.recorder.update(streams, overlays=overlays)
        return streams


    def start_recording(self):
        if self.recorder is None:
            return
        rs_cfg = self.rs_camera.cfg
        calibration = {
            "intrinsics": self.rs_camera.intrinsics,
            "depth_scale": self.rs_camera.depth_scale,
            "streams": list(rs_cfg.streams),
            "ir_emitter": rs_cfg.ir_emitter,
            "camera_fps": rs_cfg.fps,
            "width": rs_cfg.width,
            "height": rs_cfg.height,
        }
        self.recorder.start(calibration=calibration)


    def stop_recording(self):
        if self.recorder is not None:
            self.recorder.stop()


    def shutdown(self):
        if self.recorder is not None:
            self.recorder.stop()
        if self.viewer is not None:
            self.viewer.shutdown()
        self.rs_camera.shutdown()
        self._is_alive = False


    @property
    def is_alive(self):
        return self._is_alive
