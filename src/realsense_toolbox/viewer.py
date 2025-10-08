import cv2
import time
import numpy as np
from .utils import quit_keypress, draw_overlays, adjust_depth_image


class Viewer:
    def __init__(self, serial, config: dict):
        self.serial = serial
        self.show_color = config["show_color"]
        self.show_depth = config["show_depth"]
        self.fps = config["fps"]

        self.frame_interval = 1.0 / self.fps if self.fps > 0 else 0
        self.last_update_time = 0

        if self.show_color and self.show_depth:
            self.name = f"Camera {self.serial[-3:]} View"
        elif self.show_color:
            self.name = f"Camera {self.serial[-3:]} Color"
        elif self.show_depth:
            self.name = f"Camera {self.serial[-3:]} Depth"

        cv2.namedWindow(self.name, cv2.WINDOW_NORMAL)

        self.viewer_alive = True


    def update(self, color_image, depth_image, overlays=None):
        current_time = time.time()
        if current_time - self.last_update_time < self.frame_interval:
            return self.viewer_alive

        self.last_update_time = current_time

        display_image = None

        if overlays:
            color_image = draw_overlays(color_image, overlays)

        if self.show_color and self.show_depth:
            depth_colormap = adjust_depth_image(depth_image)
            display_image = np.hstack((color_image, depth_colormap))

        elif self.show_color:
            display_image = color_image

        elif self.show_depth:
            display_image = adjust_depth_image(depth_image)
        
        else:
            h, w, _ = color_image.shape
            display_image = np.zeros((h, w, 3), dtype=np.uint8)
            msg = "No streams fetched"
            text_size = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            text_x = (w - text_size[0]) // 2; text_y = (h + text_size[1]) // 2
            cv2.putText(display_image, msg, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow(self.name, display_image)
       
        if quit_keypress() or cv2.getWindowProperty(self.name, cv2.WND_PROP_VISIBLE) < 1:
            cv2.destroyAllWindows()
            self.viewer_alive = False
            return self.viewer_alive

        return self.viewer_alive