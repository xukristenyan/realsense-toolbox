import cv2
import os
import time
from .utils import draw_overlays, adjust_depth_image


class Recorder:
    '''
    Records video streams from a camera in mp4:
        - color stream
        - depth stream
        - color stream with overlays (optional)
    '''
    def __init__(self, serial, config: dict):
        self.serial = serial
        self.save_dir = config["save_dir"]
        self.save_name = config["save_name"]
        self.fps = config["fps"]
        self.save_with_overlays = config["save_with_overlays"]

        self.frame_interval = 1.0 / self.fps if self.fps > 0 else 0
        self.last_update_time = 0

        self.plain_writer = None
        self.depth_writer = None
        self.overlay_writer = None
        self.is_recording = False
        self.with_overlay = False
        
        self.session_dir = os.path.join(self.save_dir, self.save_name)
        os.makedirs(self.session_dir, exist_ok=True)
        
        print(f"[Recorder] {self.serial[-3:]} ready.")


    def _initialize_writers(self, color_image, depth_image):
        height, width, _ = color_image.shape
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        plain_path = os.path.join(self.session_dir, f"cam_{self.serial[-3:]}_color.mp4")
        self.plain_writer = cv2.VideoWriter(plain_path, fourcc, self.fps, (width, height))

        depth_path = os.path.join(self.session_dir, f"cam_{self.serial[-3:]}_depth.mp4")
        self.depth_writer = cv2.VideoWriter(depth_path, fourcc, self.fps, (width, height))

        if self.save_with_overlays:
            overlay_path = os.path.join(self.session_dir, f"cam_{self.serial[-3:]}_overlay.mp4")
            self.overlay_writer = cv2.VideoWriter(overlay_path, fourcc, self.fps, (width, height))
        
        self.is_recording = True


    def update(self, color_image, depth_image, overlays=None):
        current_time = time.time()
        if current_time - self.last_update_time < self.frame_interval:
            return True
        self.last_update_time = current_time

        if not self.is_recording:
            self._initialize_writers(color_image, depth_image)

        if self.plain_writer:
            self.plain_writer.write(color_image)

        if self.depth_writer:
            depth_colormap = adjust_depth_image(depth_image)
            self.depth_writer.write(depth_colormap)

        if self.overlay_writer:
            overlay_image = draw_overlays(color_image, overlays) if overlays else color_image
            self.overlay_writer.write(overlay_image)


    def stop(self):
        if self.is_recording:
            if self.plain_writer: self.plain_writer.release()
            if self.depth_writer: self.depth_writer.release()

            if self.overlay_writer:
                self.overlay_writer.release()

            self.is_recording = False

            print(f"[Recorder] {self.serial[-3:]} recordings are saved in: {self.session_dir}")
