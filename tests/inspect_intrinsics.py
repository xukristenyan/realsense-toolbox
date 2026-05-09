"""
Print color, IR-left, IR-right intrinsics + extrinsics from a RealSense camera.

Run once to confirm whether color and IR intrinsics differ on your specific device,
and to see the IR baseline + IR-to-color extrinsics.
"""
import pyrealsense2 as rs


SERIAL = "244622072715"
WIDTH, HEIGHT, FPS = 640, 480, 30


def main():
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_device(SERIAL)
    config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    config.enable_stream(rs.stream.infrared, 1, WIDTH, HEIGHT, rs.format.y8, FPS)
    config.enable_stream(rs.stream.infrared, 2, WIDTH, HEIGHT, rs.format.y8, FPS)

    profile = pipeline.start(config)
    try:
        color_p = rs.video_stream_profile(profile.get_stream(rs.stream.color))
        irL_p = rs.video_stream_profile(profile.get_stream(rs.stream.infrared, 1))
        irR_p = rs.video_stream_profile(profile.get_stream(rs.stream.infrared, 2))

        c = color_p.get_intrinsics()
        l = irL_p.get_intrinsics()
        r = irR_p.get_intrinsics()

        def fmt(name, k):
            return (f"{name:6s}  fx={k.fx:8.3f}  fy={k.fy:8.3f}  "
                    f"ppx={k.ppx:8.3f}  ppy={k.ppy:8.3f}  "
                    f"size={k.width}x{k.height}  model={k.model}  coeffs={k.coeffs}")

        print(fmt("COLOR", c))
        print(fmt("IR-L", l))
        print(fmt("IR-R", r))

        ext_lr = irL_p.get_extrinsics_to(irR_p)
        ext_lc = irL_p.get_extrinsics_to(color_p)
        print(f"\nIR baseline (|L->R tx|): {abs(ext_lr.translation[0]):.6f} m")
        print(f"L-IR -> color translation: {ext_lc.translation}")
        print(f"L-IR -> color rotation: {ext_lc.rotation}")

    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
