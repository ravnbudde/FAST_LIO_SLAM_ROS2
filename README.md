# FAST_LIO_SLAM_ROS2

ROS 2 full LiDAR SLAM stack that runs Fast-LIO odometry and SC-PGO pose graph optimization together.

The default bringup launches both processing nodes as ROS 2 components in one multithreaded component container. Fast-LIO publishes its body-frame registered cloud to an internal stack topic consumed by SC-PGO with intra-process comms enabled. Fast-LIO odometry is also published as a normal ROS topic so other nodes can subscribe to it.

## Dependencies

SC-PGO needs GTSAM.
```bash
sudo apt install -y \
    build-essential \
    cmake \
    git \
    libboost-all-dev \
    libeigen3-dev \
    libtbb-dev
mkdir -p ~/third_party
cd ~/third_party
rm -rf gtsam
git clone https://github.com/borglab/gtsam.git
cd gtsam
git checkout 4.2
cmake -S . -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DGTSAM_BUILD_TESTS=OFF \
    -DGTSAM_BUILD_EXAMPLES_ALWAYS=OFF \
    -DGTSAM_BUILD_UNSTABLE=ON \
    -DGTSAM_USE_SYSTEM_EIGEN=ON \
    -DCMAKE_INSTALL_PREFIX=/usr/local
cmake --build build -j$(nproc)
sudo cmake --install build
sudo ldconfig

# Verify install
find /usr/local -name "GTSAMConfig.cmake"
find /usr/local -name "*gtsam_unstable*"
```

## Packages

- `FAST-LIO2` (`fast_lio`): LiDAR-inertial odometry front-end. This repo uses the composed-node version and provides `fast_lio::LaserMappingNode`.
- `SC-PGO` (`aloam_velodyne`): Scan Context pose graph optimization back-end. It supports both normal executable use and component use through `aloam_velodyne::LaserPGONode`.
- `fast_lio_slam_bringup`: parent bringup package for the composed full-stack launch.

## Inputs

Required:

- LiDAR points: `sensor_msgs/msg/PointCloud2`
- IMU: `sensor_msgs/msg/Imu`

Optional:

- GNSS: `sensor_msgs/msg/NavSatFix`

Default external input topics:

```text
/points_raw
/imu/data
/gps/fix
```

All are launch arguments, so they can be remapped without editing code.

## Outputs

Fast-LIO outputs used by the stack:

```text
/fast_lio_slam/points/body       sensor_msgs/msg/PointCloud2
/fast_lio_slam/odometry/local    nav_msgs/msg/Odometry
```

SC-PGO outputs:

```text
/aft_pgo_odom        nav_msgs/msg/Odometry
/aft_pgo_path        nav_msgs/msg/Path
/aft_pgo_map         sensor_msgs/msg/PointCloud2
/loop_scan_local     sensor_msgs/msg/PointCloud2
/loop_submap_local   sensor_msgs/msg/PointCloud2
```

SC-PGO saved output files under `save_directory`:

```text
optimized_poses.txt
odom_poses.txt
times.txt
singlesession_posegraph.g2o
Scans/*.pcd
SCDs/*.scd
```

`Scans/` and `SCDs/` are recreated when SC-PGO starts. Use a new `save_directory` for each run you want to keep.

## Compact disk usage clone

To avoid downloading old documentation/media blobs from submodule history, clone the parent shallowly and initialize submodules as shallow single-branch checkouts:

```bash
git clone --depth 1 --single-branch --no-recurse-submodules https://github.com/ravnbudde/FAST_LIO_SLAM_ROS2.git
cd FAST_LIO_SLAM_ROS2
git submodule update --init --recursive --depth 1 --single-branch
```

## Build

Initialize submodules first, including Fast-LIO's nested `ikd-Tree` submodule:

```bash
git submodule update --init --recursive
```

Build from the ROS workspace root:

```bash
colcon build --packages-select fast_lio aloam_velodyne fast_lio_slam_bringup
source install/setup.bash
```

If another checkout of `aloam_velodyne` exists in the same workspace, remove it or build only this repo's package paths to avoid duplicate package names.

## Full Stack Launch

Default launch:

```bash
ros2 launch fast_lio_slam_bringup fast_lio_slam.launch.py
```

Example with custom topics and simulated time:

```bash
ros2 launch fast_lio_slam_bringup fast_lio_slam.launch.py \
  use_sim_time:=true \
  lidar_topic:=/your/lidar/points \
  imu_topic:=/your/imu \
  gnss_topic:=/your/gps/fix \
  save_directory:=/tmp/sc_pgo_run/
```

Useful launch arguments:

```text
fast_lio_config_file       Fast-LIO YAML config, default lw_vlp16.yaml
fast_lio_config_path       Directory containing Fast-LIO YAML configs
lidar_topic                External LiDAR PointCloud2 input
imu_topic                  External IMU input
gnss_topic                 Optional GNSS input for SC-PGO altitude factor
internal_body_cloud_topic  Internal Fast-LIO to SC-PGO body cloud topic
internal_odometry_topic    Fast-LIO odometry topic, also public for other nodes
save_directory             SC-PGO saved output directory
rviz                       Start RViz when true
```

## Rosbag Verification

For bag replay, launch the stack with `use_sim_time:=true`, then play the bag in another terminal:

```bash
ros2 launch fast_lio_slam_bringup fast_lio_slam.launch.py \
  use_sim_time:=true \
  lidar_topic:=/points_raw \
  imu_topic:=/imu/data \
  gnss_topic:=/gps/fix \
  save_directory:=/tmp/sc_pgo_bag_run/
```

```bash
ros2 bag play <bag_directory>
```

Check the main outputs:

```bash
ros2 topic hz /fast_lio_slam/odometry/local
ros2 topic hz /fast_lio_slam/points/body
ros2 topic echo /aft_pgo_odom
```

## Standalone Modes

Fast-LIO can still run standalone:

```bash
ros2 run fast_lio fastlio_mapping
```

SC-PGO can still run as a normal process:

```bash
ros2 run aloam_velodyne alaserPGO --ros-args \
  -p save_directory:=/tmp/sc_pgo/ \
  -r /aft_mapped_to_init:=/fast_lio_slam/odometry/local \
  -r /velodyne_cloud_registered_local:=/fast_lio_slam/points/body \
  -r /gps/fix:=/gps/fix
```

The full-stack bringup uses the composed SC-PGO component instead.

## Changes In Child Repos

`FAST-LIO2`:

- Uses the existing ROS 2 component target `fast_lio::LaserMappingNode`.
- The composed bringup overrides `common.lid_topic` and `common.imu_topic` from launch arguments.
- The body-frame cloud `/cloud_registered_body` is remapped to `/fast_lio_slam/points/body`.
- Odometry `/Odometry` is remapped to `/fast_lio_slam/odometry/local` and remains externally subscribable.

`SC-PGO`:

- Added component support via `aloam_velodyne::LaserPGONode`.
- Kept the normal `alaserPGO` executable as a thin wrapper around the same node.
- Added `rclcpp_components` build/runtime support.
- Preserved SC-PGO algorithm behavior, saved outputs, RViz config, and offline map utility.
- Added safe worker-thread shutdown for component container unload/shutdown.

`fast_lio_slam_bringup`:

- New parent launch package.
- Provides `fast_lio_slam.launch.py`, which loads Fast-LIO and SC-PGO into one `component_container_mt` with intra-process comms enabled.
