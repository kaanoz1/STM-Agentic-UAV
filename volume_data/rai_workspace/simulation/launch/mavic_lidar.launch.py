"""Launch Webots Mavic 2 PRO with lidar, TF tree, pose broadcaster, and RViz."""

import os

import launch
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from webots_ros2_driver.webots_controller import WebotsController
from webots_ros2_driver.webots_launcher import WebotsLauncher

SIM_DIR = '/rai/rai_workspace/simulation'
LIDAR_Z = '0.05'


def generate_launch_description():
    use_rviz = LaunchConfiguration('rviz')

    webots = WebotsLauncher(
        world=os.path.join(SIM_DIR, 'worlds', 'mavic_world.wbt'),
        mode='fast',
        ros2_supervisor=True,
    )

    driver = WebotsController(
        robot_name='Mavic_2_PRO',
        parameters=[{
            'robot_description': os.path.join(SIM_DIR, 'resource', 'mavic_webots.urdf'),
        }],
        respawn=True,
    )

    pose_broadcaster = ExecuteProcess(
        cmd=['python3', os.path.join(SIM_DIR, 'pose_broadcaster.py')],
        output='screen',
        respawn=True,
    )

    base_to_lidar = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_base_to_lidar',
        arguments=[
            '--z', LIDAR_Z,
            '--frame-id', 'base_link',
            '--child-frame-id', 'lidar',
        ],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(SIM_DIR, 'mavic.rviz')],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='false'),
        webots,
        webots._supervisor,
        driver,
        pose_broadcaster,
        base_to_lidar,
        rviz,
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=webots,
                on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
            )
        ),
    ])
