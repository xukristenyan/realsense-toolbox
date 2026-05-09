import time
import threading
import numpy as np
import pyrealsense2 as rs

from .config import RealSenseConfig


class RealSenseCamera:
    """
    Stream from a single Intel RealSense camera in a background thread.

    Access images via attributes (color_image, depth_image, left_ir_image,
    right_ir_image — only the streams enabled in config are populated) or
    via get_current_state() for a snapshot dict under lock.
    """

    def __init__(self, serial, config=None):
        if not serial:
            raise ValueError("Missing camera serial number. Check bottom of device to find.")
        self.serial = serial

        if config is None:
            config = RealSenseConfig()
        elif isinstance(config, dict):
            config = RealSenseConfig(**config)
        self.cfg = config

        self._has_color = "color" in self.cfg.streams
        self._has_depth = "depth" in self.cfg.streams
        self._has_ir_stereo = "ir_stereo" in self.cfg.streams

        self._pipeline = rs.pipeline()
        self._pipeline_config = rs.config()
        self._align = (rs.align(rs.stream.color)
                       if (self._has_color and self._has_depth) else None)

        self._depth_filters = [rs.spatial_filter(), rs.temporal_filter()] if self._has_depth else []

        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._started = False

        self.color_image = None
        self.depth_image = None
        self.left_ir_image = None
        self.right_ir_image = None

        self.intrinsics = None
        self.depth_scale = None


    def launch(self):
        try:
            self._pipeline_config.enable_device(self.serial)

            if self._has_color:
                self._pipeline_config.enable_stream(
                    rs.stream.color, self.cfg.width, self.cfg.height, rs.format.bgr8, self.cfg.fps)
            if self._has_depth:
                self._pipeline_config.enable_stream(
                    rs.stream.depth, self.cfg.width, self.cfg.height, rs.format.z16, self.cfg.fps)
            if self._has_ir_stereo:
                self._pipeline_config.enable_stream(
                    rs.stream.infrared, 1, self.cfg.width, self.cfg.height, rs.format.y8, self.cfg.fps)
                self._pipeline_config.enable_stream(
                    rs.stream.infrared, 2, self.cfg.width, self.cfg.height, rs.format.y8, self.cfg.fps)

            profile = self._pipeline.start(self._pipeline_config)
            self._started = True

            self._capture_intrinsics(profile)

            device = profile.get_device()

            if self._has_color:
                color_sensor = device.first_color_sensor()
                if color_sensor.supports(rs.option.enable_auto_exposure):
                    color_sensor.set_option(
                        rs.option.enable_auto_exposure, int(self.cfg.color_auto_exposure))

            depth_sensor = device.first_depth_sensor()
            self.depth_scale = depth_sensor.get_depth_scale()

            if self._has_depth and depth_sensor.supports(rs.option.enable_auto_exposure):
                depth_sensor.set_option(
                    rs.option.enable_auto_exposure, int(self.cfg.depth_auto_exposure))

            if depth_sensor.supports(rs.option.emitter_enabled):
                depth_sensor.set_option(rs.option.emitter_enabled, int(self.cfg.ir_emitter))

            for _ in range(30):
                self._pipeline.wait_for_frames()

            self._thread = threading.Thread(target=self._update_frame, daemon=True)
            self._thread.start()

            print(f"[RealSense {self.serial[-3:]}] Launched!")

        except Exception as e:
            print(f"[RealSense {self.serial[-3:]}] Failed to launch ({type(e).__name__}: {e})")
            self.shutdown()
            raise


    def _capture_intrinsics(self, profile):
        def _k_from_intr(intr):
            return np.array([
                [intr.fx, 0, intr.ppx],
                [0, intr.fy, intr.ppy],
                [0, 0, 1],
            ])

        # canonical intrinsics priority: color > ir_stereo > depth.
        if self._has_color:
            canon = rs.video_stream_profile(profile.get_stream(rs.stream.color)).get_intrinsics()
        elif self._has_ir_stereo:
            canon = rs.video_stream_profile(profile.get_stream(rs.stream.infrared, 1)).get_intrinsics()
        else:
            canon = rs.video_stream_profile(profile.get_stream(rs.stream.depth)).get_intrinsics()

        self.intrinsics = {
            "matrix": _k_from_intr(canon),
            "raw": canon,
            "baseline": None,
            "ir_matrix": None,
            "ir_raw": None,
            "ir_to_color": None,
        }

        if self._has_ir_stereo:
            left_p = rs.video_stream_profile(profile.get_stream(rs.stream.infrared, 1))
            right_p = rs.video_stream_profile(profile.get_stream(rs.stream.infrared, 2))
            ir = left_p.get_intrinsics()
            ir_extr = left_p.get_extrinsics_to(right_p)
            self.intrinsics["baseline"] = float(abs(ir_extr.translation[0]))
            self.intrinsics["ir_raw"] = ir
            self.intrinsics["ir_matrix"] = _k_from_intr(ir)

            if self._has_color:
                color_p = rs.video_stream_profile(profile.get_stream(rs.stream.color))
                ir2col = left_p.get_extrinsics_to(color_p)
                self.intrinsics["ir_to_color"] = {
                    "rotation": np.array(ir2col.rotation, dtype=np.float64).reshape(3, 3),
                    "translation": np.array(ir2col.translation, dtype=np.float64),
                    "raw": ir2col,
                }


    def _update_frame(self):
        while not self._stop_event.is_set():
            try:
                frames = self._pipeline.wait_for_frames(timeout_ms=1000)
                if not frames:
                    continue

                if self._align is not None:
                    frames = self._align.process(frames)

                color = frames.get_color_frame() if self._has_color else None
                depth = frames.get_depth_frame() if self._has_depth else None
                left_ir = frames.get_infrared_frame(1) if self._has_ir_stereo else None
                right_ir = frames.get_infrared_frame(2) if self._has_ir_stereo else None

                if (self._has_color and not color) or \
                   (self._has_depth and not depth) or \
                   (self._has_ir_stereo and (not left_ir or not right_ir)):
                    continue

                if depth is not None:
                    for f in self._depth_filters:
                        depth = f.process(depth)

                with self._lock:
                    if color is not None:
                        self.color_image = np.asanyarray(color.get_data())
                    if depth is not None:
                        self.depth_image = np.asanyarray(depth.get_data())
                    if left_ir is not None:
                        self.left_ir_image = np.asanyarray(left_ir.get_data())
                    if right_ir is not None:
                        self.right_ir_image = np.asanyarray(right_ir.get_data())

            except Exception as e:
                print(f"[RealSense {self.serial[-3:]}] Error in capture thread: {e}")
                time.sleep(0.5)


    def get_current_state(self):
        with self._lock:
            imgs = {
                "color": self.color_image,
                "depth": self.depth_image,
                "left_ir": self.left_ir_image,
                "right_ir": self.right_ir_image,
            }
            return {k: v for k, v in imgs.items() if v is not None}


    def get_intrinsics(self):
        return self.intrinsics


    def get_depth_scale(self):
        return self.depth_scale


    def deproject_pixel_to_point(self, xy):
        """(u, v) pixel -> 3D point (meters) in the camera frame. Requires 'depth' enabled."""
        if not self._has_depth or self.intrinsics is None or self.depth_scale is None:
            raise RuntimeError(
                "deproject_pixel_to_point requires the 'depth' stream and a launched camera.")
        u, v = int(xy[0]), int(xy[1])
        with self._lock:
            if self.depth_image is None:
                return None
            depth_units = int(self.depth_image[v, u])
        if depth_units == 0:
            return None
        depth_m = depth_units * self.depth_scale
        return rs.rs2_deproject_pixel_to_point(self.intrinsics["raw"], [u, v], depth_m)


    def shutdown(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self._started:
            self._pipeline.stop()
            self._started = False
        print(f"[RealSense {self.serial[-3:]}] Shutdown complete.")
