import time
import threading
import numpy as np
import pyrealsense2 as rs


class RealSenseCamera:
    '''
    To manage and stream data from a single Intel RealSense camera.
    It handles device initialization, configuration, and continuous frame capture in a background thread.
    '''
    def __init__(self, serial, config: dict):
        self.serial = serial
        if not self.serial:
            raise ValueError("Missing camera serial number. Check bottom of device to find.")
            
        self.fps = config.get("fps", 30)
        self.width = config.get("width", 640)
        self.height = config.get("height", 480)
        self.color_auto_exposure = config.get("color_auto_exposure", True)
        self.depth_auto_exposure = config.get("depth_auto_exposure", True)

        self._pipeline = rs.pipeline()
        self._config = rs.config()
        self._align = rs.align(rs.stream.color)
        
        # to improve depth data
        self._filters = [
            rs.spatial_filter(),
            rs.temporal_filter(),
            rs.hole_filling_filter(),
        ]
        
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        self.color_frame = None
        self.depth_frame = None
        self.color_image = None
        self.depth_image = None
        self.intrinsics = None


    def launch(self):
        try:
            self._config.enable_device(self.serial)
            self._config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
            self._config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)

            profile = self._pipeline.start(self._config)

            self._get_and_store_intrinsics(profile)

            device = profile.get_device()

            color_sensor = device.first_color_sensor()
            if color_sensor.supports(rs.option.enable_auto_exposure):
                color_sensor.set_option(rs.option.enable_auto_exposure, int(self.color_auto_exposure))

            depth_sensor = device.first_depth_sensor()
            if depth_sensor.supports(rs.option.enable_auto_exposure):
                depth_sensor.set_option(rs.option.enable_auto_exposure, int(self.depth_auto_exposure))

            for _ in range(30):
                self._pipeline.wait_for_frames()

            self._thread = threading.Thread(target=self._update_frame, daemon=True)
            self._thread.start()

            print(f"[RealSense {self.serial[-3:]}] Launched!")

        except:
            print(f"[RealSense {self.serial[-3:]}] Failed to launch. Check camera connection!")


    def _get_and_store_intrinsics(self, profile):

        color_profile = rs.video_stream_profile(profile.get_stream(rs.stream.color))
        intr = color_profile.get_intrinsics()
        
        self.intrinsics = {
            "raw": intr,
            "fx": intr.fx,
            "fy": intr.fy,
            "ppx": intr.ppx,
            "ppy": intr.ppy,
            "coeffs": intr.coeffs,
            "matrix": np.array([
                [intr.fx, 0, intr.ppx],
                [0, intr.fy, intr.ppy],
                [0, 0, 1]
            ])
        }


    def _update_frame(self):
        while not self._stop_event.is_set():
            try:
                frames = self._pipeline.wait_for_frames(timeout_ms=1000)
                if not frames:
                    continue

                aligned_frames = self._align.process(frames)
                color_frame = aligned_frames.get_color_frame()
                depth_frame = aligned_frames.get_depth_frame()

                if not color_frame or not depth_frame:
                    continue
                
                for filter in self._filters:
                    depth_frame = filter.process(depth_frame)

                with self._lock:
                    self.color_frame = color_frame
                    self.depth_frame = depth_frame
                    self.color_image = np.asanyarray(color_frame.get_data())
                    self.depth_image = np.asanyarray(depth_frame.get_data())

            except Exception as e:
                print(f"[RealSense {self.serial[-3:]}] Error in camera thread: {e}")
                time.sleep(0.5)


    def get_current_state(self):
        with self._lock:
            return self.color_image, self.depth_image, self.color_frame, self.depth_frame


    def get_images(self):
        with self._lock:
            return self.color_image, self.depth_image


    def get_frames(self):
        with self._lock:
            return self.color_frame, self.depth_frame


    def get_intrinsics(self):
        return self.intrinsics


    def deproject_pixel_to_point(self, xy, depth_frame):
        '''
        xy: 2D point (on image)
        depth_frame: (W, H) depth image
        
        camera perspective. X: into the page.
          (0, 0).____________
                |   z        |
                |    X-> x   |
                |    |       |
                |  y v       |
                |____________|        
        '''
        u, v = int(xy[0]), int(xy[1])
        depth = depth_frame.get_distance(u, v)
        if depth == 0:
            return None

        xyz = rs.rs2_deproject_pixel_to_point(self.intrinsics["raw"], [u, v], depth)

        return xyz


    def shutdown(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        
        self._pipeline.stop()

        print(f"[RealSense {self.serial[-3:]}] Shutdown complete.")
