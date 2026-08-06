import math
import time
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from rai_workspace.tools.GetLookingDirection import GetLookingDirectionTool


def _wrap_signed(angle_deg: float) -> float:
    """Wrap an angle into (-180, 180]."""
    return (angle_deg + 180.0) % 360.0 - 180.0


class ChangeLookingDirectionInput(BaseModel):
    target_looking_difference_angle: float = Field(
        description=(
            "How far to rotate the UAV, in degrees. "
            "Positive turns clockwise (north -> east), negative turns "
            "counter-clockwise (north -> west)."
        ),
    )
    timeout_sec: float = Field(
        default=30.0,
        description="Timeout duration for tool call",
    )


class ChangeLookingDirection(BaseTool):
    connector: ROS2Connector

    name: str = "ChangeLookingDirection"
    description: str = (
        "Rotates the UAV in place (yaw) by a given number of degrees relative to "
        "its current heading. Positive values turn clockwise (north -> east -> south), "
        "negative values turn counter-clockwise. "
        "Any angle is accepted, not just multiples of 90. Fractional values such as "
        "31.4 or -7.8 are valid and are executed exactly as given. When rotating to "
        "face a target, always pass the precise angle returned by "
        "CalculateTheAngleAndDistanceBetweenTheTargetTool without rounding it to the "
        "nearest 90, 45 or whole degree, because rounding introduces a heading error "
        "that grows with distance and will cause the UAV to miss the target. "
        "180 faces the opposite direction, 90 turns right, -90 turns left. "
        "Returns the final heading reached."
    )

    args_schema: Type[ChangeLookingDirectionInput] = ChangeLookingDirectionInput  # type: ignore

    cmd_vel_topic_name: str = Field(default="/cmd_vel")
    yaw_power: float = Field(default=1.0)
    min_yaw_power: float = Field(default=0.15)
    slowdown_angle: float = Field(default=30.0)
    tolerance: float = Field(default=0.1)

    def _publish_yaw(self, yaw: float) -> None:
        payload = {
            "linear": {
                "x": 0,
                "y": 0,
                "z": 0,
            },
            "angular": {
                "x": 0,
                "y": 0,
                "z": yaw,
            },
        }

        self.connector.send_message(
            ROS2Message(payload=payload),
            target=self.cmd_vel_topic_name,
            msg_type="geometry_msgs/msg/Twist",
        )

    def _yaw_command(self, error: float) -> float:
        """Proportional yaw rate, scaled down near the target to limit overshoot."""
        scale = min(1.0, abs(error) / self.slowdown_angle)
        magnitude = max(self.min_yaw_power, self.yaw_power * scale)
        return -math.copysign(magnitude, error)

    def _run(
        self,
        target_looking_difference_angle: float = 180.0,
        timeout_sec: float = 30.0,
    ) -> str:
        direction_tool = GetLookingDirectionTool(connector=self.connector)

        start_bearing: float = direction_tool.get_bearing_from_north()
        target_bearing: float = (start_bearing + target_looking_difference_angle) % 360.0

        timeout_time: float = time.time() + timeout_sec
        current_bearing: float = start_bearing

        while time.time() < timeout_time:
            current_bearing = direction_tool.get_bearing_from_north()
            error: float = _wrap_signed(target_bearing - current_bearing)

            if abs(error) <= self.tolerance:
                self._publish_yaw(0.0)
                return (
                    f"Completed. Heading: {current_bearing:.1f} degrees from north "
                    f"(target {target_bearing:.1f}, started at {start_bearing:.1f}, "
                    f"rotated {_wrap_signed(current_bearing - start_bearing):+.1f} degrees). "
                    f"{direction_tool._run()}"
                )

            self._publish_yaw(self._yaw_command(error) / 2)
            time.sleep(0.2)

        self._publish_yaw(0.0)
        remaining = _wrap_signed(target_bearing - current_bearing)
        return (
            f"Timed out after {timeout_sec:.1f} s. "
            f"Heading: {current_bearing:.1f} degrees from north, "
            f"target was {target_bearing:.1f} degrees "
            f"({abs(remaining):.1f} degrees short). "
            f"{direction_tool._run()}"
        )