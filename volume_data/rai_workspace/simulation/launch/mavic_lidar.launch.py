import os
import launch
from launch import LaunchDescription
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.webots_controller import WebotsController

SIM_DIR = '/rai/rai_workspace/simulation'


def generate_launch_description():
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

    return LaunchDescription([
        webots,
        webots._supervisor,
        driver,
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=webots,
                on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
            )
        ),
    ])
