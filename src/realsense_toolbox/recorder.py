import json
import time
from pathlib import Path

import cv2
import numpy as np

from .config import RecorderConfig
from .utils import draw_overlays


class Recorder:
    """Records selected streams from a camera. Explicit start() / stop().

    Behavior follows cfg.streams (same vocabulary as RealSenseConfig.streams):
        - "color":     color.mp4 always; color.npz also if "ir_stereo" enabled.
        - "depth":     depth.mp4 (lossy colormap, visual only).
        - "ir_stereo": left_ir.npz + right_ir.npz + calibration.json.

    npz streams are buffered in memory during recording and saved at stop().
    Memory cost: ~5–10 MB per second of IR pair at 10 fps; budget for your
    expected session length.
    """

    def __init__(self, serial, config=None):
        self.serial = serial

        if config is None:
            config = RecorderConfig()
        elif isinstance(config, dict):
            config = RecorderConfig(**config)
        self.cfg = config

        self._wants_color = "color" in self.cfg.streams
        self._wants_depth = "depth" in self.cfg.streams
        self._wants_ir = "ir_stereo" in self.cfg.streams
        self._save_color_npz = self._wants_color and self._wants_ir

        self.frame_interval = 1.0 / self.cfg.fps if self.cfg.fps > 0 else 0
        self._last_update = 0
        self._is_recording = False
        self.session_dir = None

        self._color_mp4 = None
        self._depth_mp4 = None
        self._overlay_mp4 = None
        self._color_buf = None
        self._left_ir_buf = None
        self._right_ir_buf = None


    def start(self, calibration=None):
        """Open the session directory; write calibration.json if applicable.

        calibration: optional dict with keys 'intrinsics', 'depth_scale',
            'streams', 'ir_emitter', 'fps', 'width', 'height'. Written to
            calibration.json when "ir_stereo" is in cfg.streams.
        """
        if self._is_recording:
            return

        save_name = self.cfg.save_name or time.strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path(self.cfg.save_dir) / save_name
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if self._wants_ir:
            if calibration:
                self._write_calibration(calibration)
            else:
                print(f"[Recorder {self.serial[-3:]}] WARNING: ir_stereo recording "
                      f"started without calibration; recordings will not be self-"
                      f"contained for FFS replay.")

        if self._save_color_npz:
            self._color_buf = []
        if self._wants_ir:
            self._left_ir_buf = []
            self._right_ir_buf = []

        self._last_update = 0
        self._is_recording = True
        print(f"[Recorder {self.serial[-3:]}] start -> {self.session_dir}")


    def update(self, streams, overlays=None):
        if not self._is_recording:
            return
        now = time.time()
        if now - self._last_update < self.frame_interval:
            return
        self._last_update = now

        if self._wants_color:
            color = streams.get("color")
            if color is not None:
                self._maybe_init_color_mp4(color)
                self._color_mp4.write(color)
                if self._save_color_npz:
                    self._color_buf.append(color.copy())
                if self.cfg.save_with_overlays:
                    self._maybe_init_overlay_mp4(color)
                    img = draw_overlays(color, overlays) if overlays else color
                    self._overlay_mp4.write(img)

        if self._wants_depth:
            depth = streams.get("depth")
            if depth is not None:
                self._maybe_init_depth_mp4(depth)
                self._depth_mp4.write(self._depth_to_color(depth))

        if self._wants_ir:
            left = streams.get("left_ir")
            right = streams.get("right_ir")
            if left is not None and right is not None:
                self._left_ir_buf.append(left.copy())
                self._right_ir_buf.append(right.copy())


    def stop(self):
        if not self._is_recording:
            return
        self._is_recording = False

        if self._color_mp4 is not None:
            self._color_mp4.release()
            self._color_mp4 = None
        if self._depth_mp4 is not None:
            self._depth_mp4.release()
            self._depth_mp4 = None
        if self._overlay_mp4 is not None:
            self._overlay_mp4.release()
            self._overlay_mp4 = None

        if self._save_color_npz and self._color_buf:
            arr = np.stack(self._color_buf, axis=0)
            np.savez_compressed(self._npz_path("color"), frames=arr)
        if self._wants_ir and self._left_ir_buf:
            arr = np.stack(self._left_ir_buf, axis=0)
            np.savez_compressed(self._npz_path("left_ir"), frames=arr)
        if self._wants_ir and self._right_ir_buf:
            arr = np.stack(self._right_ir_buf, axis=0)
            np.savez_compressed(self._npz_path("right_ir"), frames=arr)

        self._color_buf = None
        self._left_ir_buf = None
        self._right_ir_buf = None

        print(f"[Recorder {self.serial[-3:]}] saved to {self.session_dir}")


    def _maybe_init_color_mp4(self, frame):
        if self._color_mp4 is None:
            h, w = frame.shape[:2]
            self._color_mp4 = self._open_mp4("color", w, h)


    def _maybe_init_depth_mp4(self, frame):
        if self._depth_mp4 is None:
            h, w = frame.shape[:2]
            self._depth_mp4 = self._open_mp4("depth", w, h)


    def _maybe_init_overlay_mp4(self, frame):
        if self._overlay_mp4 is None:
            h, w = frame.shape[:2]
            self._overlay_mp4 = self._open_mp4("overlay", w, h)


    def _open_mp4(self, stream, w, h):
        path = str(self.session_dir / f"cam_{self.serial[-3:]}_{stream}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        return cv2.VideoWriter(path, fourcc, self.cfg.fps, (w, h))


    def _npz_path(self, stream):
        return str(self.session_dir / f"cam_{self.serial[-3:]}_{stream}.npz")


    @staticmethod
    def _depth_to_color(depth):
        normalized = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        return cv2.applyColorMap(normalized, cv2.COLORMAP_JET)


    def _write_calibration(self, calibration):
        out = {}
        intr = calibration.get("intrinsics") or {}
        if intr.get("matrix") is not None:
            out["K_canonical"] = intr["matrix"].tolist()
        if intr.get("ir_matrix") is not None:
            out["K_ir"] = intr["ir_matrix"].tolist()
        if intr.get("baseline") is not None:
            out["baseline"] = float(intr["baseline"])
        i2c = intr.get("ir_to_color")
        if i2c is not None:
            out["ir_to_color_R"] = i2c["rotation"].tolist()
            out["ir_to_color_t"] = i2c["translation"].tolist()
        for key in ("depth_scale", "streams", "ir_emitter", "camera_fps", "width", "height"):
            if key in calibration:
                v = calibration[key]
                out[key] = list(v) if isinstance(v, (list, tuple, set)) else v
        out["recorder_fps"] = self.cfg.fps

        path = self.session_dir / f"cam_{self.serial[-3:]}_calibration.json"
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
