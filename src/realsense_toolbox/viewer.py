import time

import cv2
import numpy as np

from .config import ViewerConfig
from .utils import draw_overlays


class Viewer:
    """
    Display window for one camera. Pure display sink — no keyboard input.

    Accepts a streams dict (matching RealSenseCamera.get_current_state())
    and renders the streams listed in cfg.show side-by-side, rate-limited
    to cfg.fps.
    """

    def __init__(self, serial, config=None):
        self.serial = serial

        if config is None:
            config = ViewerConfig()
        elif isinstance(config, dict):
            config = ViewerConfig(**config)
        self.cfg = config

        self.frame_interval = 1.0 / self.cfg.fps if self.cfg.fps > 0 else 0
        self._last_update = 0

        self.window_name = f"Camera {serial[-3:]}"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)


    def update(self, streams, overlays=None):
        """
        streams: dict from RealSenseCamera.get_current_state().
        overlays: optional list applied to the color panel only.
        """
        now = time.time()
        if now - self._last_update < self.frame_interval:
            return
        self._last_update = now

        panels = []
        for name in self.cfg.show:
            img = streams.get(name)
            if img is None:
                continue
            panels.append(self._render_panel(name, img, overlays))

        if not panels:
            display = self._placeholder()
        elif len(panels) == 1:
            display = panels[0]
        else:
            display = np.hstack(panels)

        cv2.imshow(self.window_name, display)
        cv2.waitKey(1)


    def is_window_open(self):
        try:
            return cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            return False


    def shutdown(self):
        try:
            cv2.destroyWindow(self.window_name)
        except cv2.error:
            pass


    def _render_panel(self, name, img, overlays):
        if name == "color":
            return draw_overlays(img, overlays) if overlays else img
        if name == "depth":
            return self._depth_to_color(img)
        # left_ir / right_ir: single-channel uint8 — promote to 3-channel for hstack
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


    @staticmethod
    def _depth_to_color(depth):
        normalized = cv2.normalize(depth, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        return cv2.applyColorMap(normalized, cv2.COLORMAP_JET)


    @staticmethod
    def _placeholder(w=640, h=480):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        msg = "No streams to display"
        ts = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        cv2.putText(img, msg, ((w - ts[0]) // 2, (h + ts[1]) // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return img
