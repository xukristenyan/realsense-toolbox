# RealSense Toolbox 🚀

A flexible, modular Python toolbox for interfacing with Intel RealSense depth cameras. This toolbox is designed to simplify multi-camera setups, live viewing, and complex recording sessions through a clean, configuration-driven architecture.

## Features & Architecture

This framework is built to provide a clean, non-blocking interface for complex camera operations.

### Key Features

* **Multi-Camera Support**: Natively designed to manage multiple RealSense devices concurrently.
* **Thread-Safe Streaming**: Each camera operates in a dedicated background thread to ensure non-blocking frame acquisition.
* **Modular Design**: Functionality is cleanly separated into a core camera driver, a real-time viewer, and a data recorder.
* **Configuration-Driven**: System and camera properties are defined in a clear configuration file, allowing for easy setup changes without modifying code.
* **Real-time Visualization**: An optional, efficient viewer (powered by OpenCV) can display color and depth streams for one or more cameras.
* **Flexible Recording**: An optional recorder can save color/depth streams and metadata to disk.
* **Built-in Processing**: Includes automatic frame alignment (depth to color) and applies a series of configurable filters to enhance depth data quality.

### System Architecture

The framework is organized into a clear hierarchy of classes, where each level abstracts the complexity of the one below it.

1.  **`RealSenseCamera`**: The lowest-level class. It is a thread-safe wrapper that directly manages a single RealSense device. Its sole responsibility is to connect to the device, continuously acquire and process frames, and provide thread-safe access to the latest data (images, frames, intrinsics).

2.  **`Viewer` & `Recorder`**: These are optional, modular components that perform specific tasks. The `Viewer` handles rendering frames to the screen, while the `Recorder` handles writing frames to disk.

3.  **`Camera`**: This class acts as a high-level container for a single, complete camera setup. It instantiates and coordinates one `RealSenseCamera` object along with its optional `Viewer` and `Recorder` modules.

4.  **`System`**: The top-level manager. This class is responsible for managing a collection of `Camera` objects, allowing you to launch, update, and shut down an entire multi-camera system with simple commands.


## Installation

### Step 1: Clone this repo

Clone this repo

```bash
# With HTTP
git clone https://github.com/xukristenyan/realsense-toolbox.git

# With SSH
git clone git@github.com:xukristenyan/realsense-toolbox.git
```

### Step 2: Install

```bash
# using uv
uv add --editable [path/to/realsense-toolbox]

# using pip
pip install -e [path/to/realsense-toolbox]
```

## Usage

### Command Lines as Examples

```bash
# get images
uv run examples/run_realsense.py

# live view + recording
uv run examples/run_camera.py

# deal with multiple cameras in the environment
uv run examples/run_system.py

# generate pointcloud
uv run examples/run_point_cloud.py
```

### Default Camera Settings

You need to provide configuration for your customized camera usage. These are the default settings. You can only include those parameters different from the default values in your configuration.

```python
camera_config = {
    "enable_viewer": False,             # set to True if you need a window to see live streaming images
    "enable_recorder": False,           # set to True if you need to record the camera streaming
    
    "specifications": {
        "fps": 30,
        "width": 640,
        "height": 480,
        "color_auto_exposure": True,
        "depth_auto_exposure": True,
    },
    
    "viewer": {                         # update this dict with your preference if viewer enabled
        "fps": 30,
        "show_color": True,
        "show_depth": False,
    },
    
    "recorder": {                       # update this dict with your preference if recorder enabled 
        "fps": 10,
        "save_dir": "./recordings",
        "save_name": current_time,
        "save_with_overlays": False,
    }
}

overlays_config = [
    {"type": "dot",
     "xy": xy,
     "radius": 6,
     "color": (0, 255, 0)
     },
    {"type": "text",
     "content": text,
     "position": (50, 50),
     "color": (0, 0, 255)
     }
]

pointcloud_config = {
    "enable_depth_filter": True,
    "min_depth": 0.1,
    "max_depth": 2.0,

    "enable_prune": False,
    "bbox_min": [0.1, -0.8, -0.01],     # x, y, z min ranges
    "bbox_max": [0.8, 0.8, 0.9],        # x, y, z max ranges

    "enable_downsample": False,
    "voxel_size": 0.01                  # unit: meter
}

```