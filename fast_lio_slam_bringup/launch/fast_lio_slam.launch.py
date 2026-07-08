import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    fast_lio_share = get_package_share_directory('fast_lio')
    default_fast_lio_config_path = os.path.join(fast_lio_share, 'config')
    default_rviz_cfg = PathJoinSubstitution([
        FindPackageShare('aloam_velodyne'), 'rviz_cfg', 'aloam_velodyne.rviz'
    ])

    use_sim_time = LaunchConfiguration('use_sim_time')
    fast_lio_config_path = LaunchConfiguration('fast_lio_config_path')
    fast_lio_config_file = LaunchConfiguration('fast_lio_config_file')
    lidar_topic = LaunchConfiguration('lidar_topic')
    imu_topic = LaunchConfiguration('imu_topic')
    gnss_topic = LaunchConfiguration('gnss_topic')
    save_directory = LaunchConfiguration('save_directory')
    rviz = LaunchConfiguration('rviz')
    rviz_cfg = LaunchConfiguration('rviz_cfg')

    internal_body_cloud_topic = LaunchConfiguration('internal_body_cloud_topic')
    internal_odometry_topic = LaunchConfiguration('internal_odometry_topic')

    container = ComposableNodeContainer(
        name='fast_lio_slam_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        output='screen',
        composable_node_descriptions=[
            ComposableNode(
                package='fast_lio',
                plugin='fast_lio::LaserMappingNode',
                name='fastlio_mapping',
                parameters=[
                    PathJoinSubstitution([fast_lio_config_path, fast_lio_config_file]),
                    {
                        'use_sim_time': use_sim_time,
                        'common.lid_topic': lidar_topic,
                        'common.imu_topic': imu_topic,
                        'publish.scan_publish_en': True,
                        'publish.scan_bodyframe_pub_en': True,
                    },
                ],
                remappings=[
                    ('/cloud_registered_body', internal_body_cloud_topic),
                    ('/Odometry', internal_odometry_topic),
                ],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
            ComposableNode(
                package='aloam_velodyne',
                plugin='aloam_velodyne::LaserPGONode',
                name='alaserPGO',
                parameters=[{
                    'use_sim_time': use_sim_time,
                    'save_directory': save_directory,
                    'keyframe_meter_gap': LaunchConfiguration('keyframe_meter_gap'),
                    'keyframe_deg_gap': LaunchConfiguration('keyframe_deg_gap'),
                    'sc_dist_thres': LaunchConfiguration('sc_dist_thres'),
                    'sc_max_radius': LaunchConfiguration('sc_max_radius'),
                    'mapviz_filter_size': LaunchConfiguration('mapviz_filter_size'),
                }],
                remappings=[
                    ('/velodyne_cloud_registered_local', internal_body_cloud_topic),
                    ('/aft_mapped_to_init', internal_odometry_topic),
                    ('/gps/fix', gnss_topic),
                ],
                extra_arguments=[{'use_intra_process_comms': True}],
            ),
        ],
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_cfg],
        condition=IfCondition(rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false', description='Use ROS time from /clock'),
        DeclareLaunchArgument('fast_lio_config_path', default_value=default_fast_lio_config_path, description='Directory containing Fast-LIO YAML configs'),
        DeclareLaunchArgument('fast_lio_config_file', default_value='lw_vlp16.yaml', description='Fast-LIO YAML config filename'),
        DeclareLaunchArgument('lidar_topic', default_value='/points_raw', description='Input LiDAR PointCloud2 topic for Fast-LIO'),
        DeclareLaunchArgument('imu_topic', default_value='/imu/data', description='Input IMU topic for Fast-LIO'),
        DeclareLaunchArgument('gnss_topic', default_value='/gps/fix', description='Optional NavSatFix topic for SC-PGO altitude factor'),
        DeclareLaunchArgument('save_directory', default_value='/tmp/sc_pgo/', description='SC-PGO output directory; Scans/ and SCDs/ are recreated on startup'),
        DeclareLaunchArgument('internal_body_cloud_topic', default_value='/fast_lio_slam/points/body', description='Internal Fast-LIO body-frame cloud topic consumed by SC-PGO'),
        DeclareLaunchArgument('internal_odometry_topic', default_value='/fast_lio_slam/odometry/local', description='Fast-LIO odometry topic consumed by SC-PGO and available to external nodes'),
        DeclareLaunchArgument('keyframe_meter_gap', default_value='2.0'),
        DeclareLaunchArgument('keyframe_deg_gap', default_value='10.0'),
        DeclareLaunchArgument('sc_dist_thres', default_value='0.4'),
        DeclareLaunchArgument('sc_max_radius', default_value='80.0'),
        DeclareLaunchArgument('mapviz_filter_size', default_value='0.4'),
        DeclareLaunchArgument('rviz', default_value='false', description='Start RViz with the SC-PGO config'),
        DeclareLaunchArgument('rviz_cfg', default_value=default_rviz_cfg),
        container,
        rviz_node,
    ])
