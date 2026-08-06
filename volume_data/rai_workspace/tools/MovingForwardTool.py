import math
import time
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from geometry_msgs.msg import Point

from rai_workspace.tools.HoverWithNoSwayTool import HoverWithNoSwayTool
from rai_workspace.tools.GetCurrentPositionByGpsTool import GetCurrentPositionByGpsTool
from rai_workspace.tools.GetLookingDirection import GetLookingDirectionTool


class MovingForwardToolInput(BaseModel):
    distance: float = Field(
        description=(
            "How far to travel along the current heading, in meters. "
            "Positive moves forward, negative moves backward along the same line. "
            "Pass the distance returned by "
            "CalculateTheAngleAndDistanceBetweenTheTargetTool."
        ),
    )
    timeout_sec: float = Field(
        default=60.0,
        description="Timeout duration for tool call",
    )


class MovingForwardTool(BaseTool):
    connector: ROS2Connector

    name: str = "MovingForwardTool"
    description: str = (
        "Moves the UAV along its current heading by the given distance in meters. "
        "Positive values move forward, negative values move backward along the same "
        "line. The UAV does not turn, strafe or change altitude while moving, so the "
        "heading set by ChangeLookingDirection is preserved. "
        "If this tool was called in order to reach a target position, you MUST verify "
        "the result afterwards: call "
        "CalculateTheAngleAndDistanceBetweenTheTargetTool again with the same target_x "
        "and target_y you used before. If the returned distance is greater than 1 meter, "
        "the target has not been reached yet: rotate to the newly returned angle with "
        "ChangeLookingDirection and call MovingForwardTool again with the newly returned "
        "distance. Repeat this calculate -> rotate -> move cycle until the distance drops "
        "to 1 meter or below. Never assume the target was reached without measuring."
    )

    args_schema: Type[MovingForwardToolInput] = MovingForwardToolInput  # type: ignore

    cmd_vel_topic_name: str = Field(default="/cmd_vel")
    pitch_power: float = Field(default=1.0)
    min_pitch_power: float = Field(default=0.15)
    slowdown_distance: float = Field(default=1.5)
    tolerance: float = Field(default=1)
    forward_sign: float = Field(
        default=1.0,
        description="Set to -1.0 if a positive linear.x makes the UAV fly backward.",
    )

    def _publish_pitch(self, forward: float) -> None:
        payload = {
            "linear": {
                "x": forward,
                "y": 0.0,
                "z": 0.0,
            },
            "angular": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
            },
        }

        self.connector.send_message(
            ROS2Message(payload=payload),
            target=self.cmd_vel_topic_name,
            msg_type="geometry_msgs/msg/Twist",
        )

    def _pitch_command(self, error: float) -> float:
        """Proportional pitch, scaled down near the target to limit overshoot."""
        scale = min(1.0, abs(error) / self.slowdown_distance)
        magnitude = max(self.min_pitch_power, self.pitch_power * scale)
        return math.copysign(magnitude, error) * self.forward_sign

    def _run(self, distance: float, timeout_sec: float = 60.0) -> str:
        position_tool = GetCurrentPositionByGpsTool(connector=self.connector)
        direction_tool = GetLookingDirectionTool(connector=self.connector)

        start: Point = position_tool.get_current_point()
        heading = math.radians(direction_tool.get_heading())

        # Unit vector pointing along the heading, in ENU (x=east, y=north).
        forward_x = math.sin(heading)
        forward_y = math.cos(heading)

        timeout_time = time.time() + timeout_sec
        travelled = 0.0
        lateral = 0.0

        while time.time() < timeout_time:
            current: Point = position_tool.get_current_point()
            dx = current.x - start.x
            dy = current.y - start.y

            # Signed progress along the original heading, and sideways drift.
            travelled = dx * forward_x + dy * forward_y
            lateral = -dx * forward_y + dy * forward_x

            error = distance - travelled

            if abs(error) <= self.tolerance:
                self._publish_pitch(0.0)
                stay_tool = HoverWithNoSwayTool(connector=self.connector)
                stay_tool._run()
                return (
                    f"Completed. Travelled {travelled:.2f} m of the requested "
                    f"{distance:.2f} m (off by {error:+.2f} m, lateral drift "
                    f"{lateral:+.2f} m). Heading and altitude unchanged. "
                    f"If this was a move towards a target, call "
                    f"CalculateTheAngleAndDistanceBetweenTheTargetTool now to verify."
                )

            self._publish_pitch(self._pitch_command(error))
            time.sleep(0.1)

        self._publish_pitch(0.0)
        return (
            f"Timed out after {timeout_sec:.1f} s. "
            f"Travelled {travelled:.2f} m, target was {distance:.2f} m "
            f"({abs(distance - travelled):.2f} m short), lateral drift {lateral:+.2f} m."
        )