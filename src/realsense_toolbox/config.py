from dataclasses import dataclass, field


VALID_STREAMS = {"color", "depth", "ir_stereo"}
VALID_DISPLAY_STREAMS = {"color", "depth", "left_ir", "right_ir"}


@dataclass
class RealSenseConfig:
    """
    Config for a RealSense camera pipeline.

    streams: subset of {"color", "depth", "ir_stereo"}.
        - "color"     : RGB (BGR8). Acts as the alignment target when "depth" is also enabled.
        - "depth"     : on-device depth (Z16), aligned to color when "color" is enabled.
        - "ir_stereo" : left + right IR pair (Y8) for external stereo (e.g. Fast-FoundationStereo).
    """
    streams: list[str] = field(default_factory=lambda: ["color", "depth"])

    fps: int = 30
    width: int = 640
    height: int = 480

    color_auto_exposure: bool = True
    depth_auto_exposure: bool = True
    ir_emitter: bool | None = None    # auto: True iff "depth" in streams

    def __post_init__(self):
        if not self.streams:
            raise ValueError("streams must contain at least one entry")
        invalid = set(self.streams) - VALID_STREAMS
        if invalid:
            raise ValueError(
                f"Unknown stream id(s): {sorted(invalid)}. "
                f"Allowed: {sorted(VALID_STREAMS)}"
            )
        if self.ir_emitter is None:
            self.ir_emitter = "depth" in self.streams


@dataclass
class ViewerConfig:
    """
    Config for the Viewer (display window).

    show: subset of {"color", "depth", "left_ir", "right_ir"}. 
        Streams listed here but not present in the camera's output are silently skipped.
    fps: display rate cap; the capture thread runs faster, the viewer
        rate-limits its imshow calls to this rate.
    """
    show: list[str] = field(default_factory=lambda: ["color"])
    fps: int = 30

    def __post_init__(self):
        if not self.show:
            raise ValueError("show must contain at least one stream id")
        invalid = set(self.show) - VALID_DISPLAY_STREAMS
        if invalid:
            raise ValueError(
                f"Unknown display stream id(s): {sorted(invalid)}. "
                f"Allowed: {sorted(VALID_DISPLAY_STREAMS)}"
            )


@dataclass
class RecorderConfig:
    """
    Config for the Recorder (per-camera).

    streams: subset of {"color", "depth", "ir_stereo"}. 
        Behavior per stream:
        - "color": always saved as .mp4 (lossy, visual). 
                    Additionally saved as .npz (lossless) when "ir_stereo" is enabled.
        - "depth": saved as .mp4 colormap (lossy, visual review only).
        - "ir_stereo": left_ir.npz + right_ir.npz (lossless), plus a
                       calibration.json containing intrinsics, baseline,
                       and IR-to-color extrinsics.

    Files saved under {save_dir}/{save_name}/:
        cam_<last3>_color.mp4         (when "color" in streams)
        cam_<last3>_color.npz         (when both "color" and "ir_stereo")
        cam_<last3>_depth.mp4         (when "depth" in streams)
        cam_<last3>_left_ir.npz       (when "ir_stereo" in streams)
        cam_<last3>_right_ir.npz     (when "ir_stereo" in streams)
        cam_<last3>_overlay.mp4       (when save_with_overlays and "color")
        cam_<last3>_calibration.json  (when "ir_stereo" in streams)

    save_name: if None, auto-set to a timestamp at start() (e.g. "20260508_153023").
    fps: rate at which frames are sampled from the camera. Default 10 Hz. Up to 30 Hz.
    """
    streams: list[str] = field(default_factory=lambda: ["color"])
    save_dir: str = "./recordings"
    save_name: str | None = None
    fps: int = 10
    save_with_overlays: bool = False

    def __post_init__(self):
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if not self.streams:
            raise ValueError("streams must contain at least one entry")
        invalid = set(self.streams) - VALID_STREAMS
        if invalid:
            raise ValueError(
                f"Unknown stream id(s): {sorted(invalid)}. "
                f"Allowed: {sorted(VALID_STREAMS)}"
            )


@dataclass
class CameraConfig:
    """
    Top-level config for a Camera (RealSense + optional Viewer + optional Recorder).

    Sub-configs may be passed as dataclasses or dicts (normalized in __post_init__).
    Setting viewer=None or recorder=None disables that component.
    """
    realsense: RealSenseConfig | dict = field(default_factory=RealSenseConfig)
    viewer: ViewerConfig | dict | None = None
    recorder: RecorderConfig | dict | None = None

    def __post_init__(self):
        if isinstance(self.realsense, dict):
            self.realsense = RealSenseConfig(**self.realsense)
        if isinstance(self.viewer, dict):
            self.viewer = ViewerConfig(**self.viewer)
        if isinstance(self.recorder, dict):
            self.recorder = RecorderConfig(**self.recorder)
