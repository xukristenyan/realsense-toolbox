from .camera import Camera


class CameraSystem:
    """Coordinates multiple Camera objects.

    Pure fan-out — broadcasts start_recording / stop_recording / shutdown
    to every camera; aggregates per-camera state for is_alive and
    get_observations(). Does not own a KeyListener: the caller decides
    when to trigger recording.

    Typical use:
        system = CameraSystem({
            "244622072715": CameraConfig(realsense=..., recorder=...),
            "244622072716": CameraConfig(realsense=..., recorder=...),
        })
        system.launch()
        with KeyListener() as keys:
            while system.is_alive:
                system.get_observations()
                if keys.consume_pressed("s"):    system.start_recording()
                if keys.consume_pressed("e"):    system.stop_recording()
                if keys.consume_pressed("esc"):  break
        system.shutdown()
    """

    def __init__(self, configs):
        if not configs:
            raise ValueError("CameraSystem requires at least one camera config")
        self.cameras = {serial: Camera(serial, cfg) for serial, cfg in configs.items()}
        self._launched = False


    def launch(self):
        for cam in self.cameras.values():
            cam.launch()
        self._launched = True
        print(f"[System] launched {len(self.cameras)} camera(s)")


    def get_observations(self, overlays_by_serial=None):
        """Tick every camera. Returns {serial: streams_dict}."""
        overlays_by_serial = overlays_by_serial or {}
        return {
            serial: cam.get_observations(overlays=overlays_by_serial.get(serial))
            for serial, cam in self.cameras.items()
        }


    def start_recording(self):
        for cam in self.cameras.values():
            cam.start_recording()


    def stop_recording(self):
        for cam in self.cameras.values():
            cam.stop_recording()


    def shutdown(self):
        for cam in self.cameras.values():
            cam.shutdown()
        self._launched = False
        print("[System] shutdown complete")


    @property
    def is_alive(self):
        if not self._launched:
            return False
        for cam in self.cameras.values():
            if not cam.is_alive:
                return False
            if cam.viewer is not None and not cam.viewer.is_window_open():
                return False
        return True
