from launch import LaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    gpsd_client_dir = get_package_share_directory('gpsd_client')
    gpsd_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gpsd_client_dir, 'launch', 'gpsd_client-launch.py')
        )
    )

    boatcontrol_dir = get_package_share_directory('boatcontrol')
    boatcontrol = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(boatcontrol_dir, 'launch', 'boatcontrol.launch.py')
        )
    )

    sensorfusion_dir = get_package_share_directory('sensorfusion')
    sensorfusion = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(sensorfusion_dir, 'launch', 'sensorfusion.launch.py')
        )
    )

    nav_dir = get_package_share_directory('navigation')
    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav_dir, 'launch', 'nav2_stack.launch.py')
        )
    )

    return LaunchDescription([
        gpsd_launch,
        boatcontrol,
        sensorfusion,
        nav_launch
    ])
