from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.actions import LifecycleNode
import launch_testing.actions
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    controller_yaml = os.path.join(
        get_package_share_directory('navigation'),
        'config',
        'controller_server.yaml'
    )
    behavior_yaml = os.path.join(
        get_package_share_directory('navigation'),
        'config',
        'behavior_server.yaml'
    )
    map_yaml = os.path.join(
        get_package_share_directory('navigation'),
        'maps',
        'empty.yml'
    )
    nodes = [
        LifecycleNode(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            name='bt_navigator',
            namespace='',
            parameters=[{'use_sim_time': False}],
        ),
        LifecycleNode(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            namespace='',
            parameters=[{'use_sim_time': False}],
        ),
        LifecycleNode(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            namespace='',
            parameters=[controller_yaml],
        ),
        LifecycleNode(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            namespace='',
            parameters=[{
                'yaml_filename': map_yaml,
                'use_sim_time': False
            }],
        ),
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            parameters=[{'use_sim_time': False}],
        ),
        Node(
            package='navigation',         # Je eigen package
            executable='navigation_node', # De entrypoint (zoals in setup.py -> console_scripts)
            name='navigation_node',
            output='screen',
            parameters=[{'use_sim_time': False}]
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_map_to_odom',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_map_to_base_link',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'base_link'],
            output='screen'
        ),
        LifecycleNode(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            namespace='',
            output='screen',
            parameters=[behavior_yaml],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{
                'autostart': True,
                'node_names': [
                    'map_server',
                    'controller_server',
                    'planner_server',
                    'behavior_server',
                    'bt_navigator',
                ]
            }]
        ),
    ]

    return LaunchDescription(nodes + [
        launch_testing.actions.ReadyToTest()
    ])
