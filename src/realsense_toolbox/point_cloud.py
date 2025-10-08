import numpy as np
from pathlib import Path
import pyrealsense2 as rs
import open3d as o3d


class PointCloudGenerator():
    '''
    To generate a pointcloud of a static scene.
    '''
    def __init__(self, config, id="camera"):
        self.config = config
        self.id = id


    def generate(self, color_image, color_frame, depth_frame):

        raw_pcd = rs.pointcloud()
        raw_pcd.map_to(color_frame)
        points = raw_pcd.calculate(depth_frame)

        pcd = np.asanyarray(points.get_vertices()).view(np.float32).reshape(-1, 3)

        tex = np.asanyarray(points.get_texture_coordinates()).view(np.float32).reshape(-1, 2)
        h, w = color_image.shape[:2]
        u = np.clip((tex[:, 0] * w).astype(np.int32), 0, w - 1)
        v = np.clip((tex[:, 1] * h).astype(np.int32), 0, h - 1)
        color = color_image[v, u][:, ::-1] / 255.0

        o3d_pcd = o3d.geometry.PointCloud()
        o3d_pcd.points = o3d.utility.Vector3dVector(pcd)
        o3d_pcd.colors = o3d.utility.Vector3dVector(color)

        return o3d_pcd
    

    def filter_depth(self, o3d_pcd):
        pcd = np.asarray(o3d_pcd.points)
        color = np.asarray(o3d_pcd.colors)

        depth_filter = (
            (pcd[:, 2] > self.config.get("min_depth", 0.1)) &
            (pcd[:, 2] < self.config.get("max_depth", 2.0)) &
            np.isfinite(pcd).all(axis=1)
        )

        o3d_pcd.points = o3d.utility.Vector3dVector(pcd[depth_filter])
        o3d_pcd.colors = o3d.utility.Vector3dVector(color[depth_filter])

        return o3d_pcd


    def prune(self, o3d_pcd):
        bbox = o3d.geometry.AxisAlignedBoundingBox(
            min_bound=self.config.get("bbox_min", [0.1, -0.8, -0.01]),
            max_bound=self.config.get("bbox_max", [0.8, 0.8, 0.9])
        )
        o3d_pcd = o3d_pcd.crop(bbox)

        return o3d_pcd


    def downsample(self, o3d_pcd):
        voxel_size = self.config.get("voxel_size", 0.01)
        if voxel_size > 0:
            o3d_pcd = o3d_pcd.voxel_down_sample(voxel_size=voxel_size)

        return o3d_pcd


    def visualize(self, o3d_pcd, name=None):
        if o3d_pcd.is_empty():
            print("No point cloud to visualize")
            return

        frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
        name = name if name is not None else "Point Cloud"

        o3d.visualization.draw_geometries([o3d_pcd, frame], window_name=name)


    def get_pointcloud(self, color_image, color_frame, depth_frame, visualize=False):
        o3d_pcd = self.generate(color_image, color_frame, depth_frame)

        if self.config.get("enable_depth_filter", True):
            o3d_pcd = self.filter_depth(o3d_pcd)

        if self.config.get("enable_prune", False):
            o3d_pcd = self.prune(o3d_pcd)

        if self.config.get("enable_downsample", False):
            o3d_pcd = self.downsample(o3d_pcd)

        if visualize:
            self.visualize(o3d_pcd, name=f"point_cloud_{self.id}")

        return o3d_pcd


    def save(self, o3d_pcd, save_dir, filename="point_cloud.ply"):
        if o3d_pcd.is_empty():
            print("No point cloud to save")
            return

        if not filename.endswith(".ply"):
            filename += ".ply"

        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        out_path = save_path / filename
        o3d.io.write_point_cloud(str(out_path), o3d_pcd, write_ascii=False)

        print("Point cloud saved!")
