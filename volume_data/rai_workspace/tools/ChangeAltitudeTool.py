import time

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from geometry_msgs.msg import Twist, Point
from rai_workspace.tools.GetCurrentPositionByGpsTool import GetCurrentPositionByGpsTool

from typing import Type

class ChangeAltitudeToolInput(BaseModel):
    target_altitude: float = Field(
        description="Target altitude in meters.",
    )
    timeout_sec: float = Field(
        default=30.0,
        description="Timeout duration for tool call",
    )


class ChangeAltitudeTool(BaseTool):
    connector: ROS2Connector

    name: str = "ChangeAltitudeTool"
    description: str = (
        "Makes the UAV take off or decent to a target altitude. "
        "Returns the final altitude reached. "
        "This tool can be used in order to land the UAV with the target_altitude parameter 1. "
        "Use 10 for default altitude. "
        "Maximum target_altitude parameter should be 30"
        "Minimum target_altitude parameter should be 1"
    )

    args_schema: Type[ChangeAltitudeToolInput] = ChangeAltitudeToolInput # type: ignore

    cmd_vel_topic_name: str = Field(default="/cmd_vel")
    gas_power: float = Field(default=1.0)
    tolerance: float = Field(default=0.1)

    def _publish_climb(self, vertical: float) -> None:
        payload = {
            "linear": {
                "x": 0,
                "y": 0,
                "z": vertical
            },
            "angular": {
                "x": 0,
                "y": 0,
                "z": 0
            }
        }
       
        self.connector.send_message(
            ROS2Message(payload=payload),
            target=self.cmd_vel_topic_name,
            msg_type="geometry_msgs/msg/Twist",
        )

    def _run(self, target_altitude: float, timeout_sec: float = 30) -> str:
        current_poisition_tool = GetCurrentPositionByGpsTool(connector=self.connector)
        start_altitude: Point = current_poisition_tool.get_current_point()

        timeout_time: float = time.time() + timeout_sec

        current_altitude: Point = start_altitude

        while time.time() < timeout_time:
            current_point: Point = current_poisition_tool.get_current_point()
            current_altitude: Point = current_point

            error: float = target_altitude - current_altitude.z

            if abs(error) <= self.tolerance:
                self._publish_climb(0.0)
                return (
                    f"Completed. Altitude: {current_altitude.z:.2f} m "
                    f"(target {target_altitude:.2f} m, started at {start_altitude.z:.2f} m)."
                )

            self._publish_climb(self.gas_power if error > 0 else -self.gas_power * 2 / 3)
            time.sleep(0.1)

        self._publish_climb(0.0)
        return (
            f"Timed out after {timeout_sec:.1f} s. "
            f"Altitude: {current_altitude.z:.2f} m, target was {target_altitude:.2f} m."
        )