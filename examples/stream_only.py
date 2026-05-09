"""
Stream directly from a RealSense camera (no Camera/Viewer/Recorder).

Saves N frames per enabled stream to disk and prints calibration.
SSH-friendly. Edit `config` to switch between modes (e.g. ir_stereo).
"""
import time
from pathlib import Path

import cv2

from realsense_toolbox import RealSenseCamera
from realsense_toolbox.config import RealSenseConfig


def main():
    # ===== YOUR CHANGES =====
    serial = "244622072715"

    config = RealSenseConfig(
        streams=["color", "depth"],
        # streams=["color", "ir_stereo"],   # uncomment to test FoundationStereo path
        # ir_emitter=False,
    )

    out_dir = Path("./recordings/smoke_test")
    n_frames = 5
    # ========================

    out_dir.mkdir(parents=True, exist_ok=True)

    camera = RealSenseCamera(serial, config)
    try:
        camera.launch()

        intr = camera.get_intrinsics()
        print(f"\ndepth_scale: {camera.get_depth_scale()}")
        print(f"K (canonical):\n{intr['matrix']}")
        if intr["baseline"] is not None:
            print(f"baseline: {intr['baseline']:.6f} m")
        if intr["ir_matrix"] is not None:
            print(f"K_ir:\n{intr['ir_matrix']}")
        if intr["ir_to_color"] is not None:
            print(f"IR->color translation: {intr['ir_to_color']['translation']}")
            print(f"IR->color rotation:\n{intr['ir_to_color']['rotation']}")

        # Wait up to 5s for first frame
        for _ in range(100):
            if camera.get_current_state():
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("No frames received within 5s")

        for i in range(n_frames):
            state = camera.get_current_state()
            if not state:
                time.sleep(0.05)
                continue
            for name, img in state.items():
                if name == "depth":
                    colormap = cv2.applyColorMap(
                        cv2.convertScaleAbs(img, alpha=0.03), cv2.COLORMAP_JET)
                    cv2.imwrite(str(out_dir / f"{i:03d}_depth_colormap.png"), colormap)
                    cv2.imwrite(str(out_dir / f"{i:03d}_depth.png"), img)  # raw 16-bit
                else:
                    cv2.imwrite(str(out_dir / f"{i:03d}_{name}.png"), img)
            time.sleep(0.1)

        print(f"\nSaved {n_frames} frames/stream to {out_dir.resolve()}")
        print(f"Streams captured: {list(state.keys())}")

    finally:
        camera.shutdown()


if __name__ == "__main__":
    main()
