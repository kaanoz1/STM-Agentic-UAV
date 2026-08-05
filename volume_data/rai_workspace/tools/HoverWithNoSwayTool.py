import time
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message


class HoverWithNoSwayToolInput(BaseModel):
    duration: float = Field(
        default=1.0,
        description="How many seconds to keep publishing the zero command.",
    )


class HoverWithNoSwayTool(BaseTool):
    connector: ROS2Connector

    name: str = "HoverWithNoSwayTool"
    description: str = (
        "Stops all UAV motion and holds the current position and heading. "
        "Sends a zero velocity command (no forward/lateral/vertical movement, "
        "no yaw rotation) so the UAV hovers in place without sway. "
        "Use this before taking a measurement, between movement steps, or to "
        "abort an ongoing motion."
    )

    args_schema: Type[HoverWithNoSwayToolInput] = HoverWithNoSwayToolInput # type: ignore

    cmd_vel_topic_name: str = Field(default="/cmd_vel")
    publish_rate_hz: float = Field(default=10.0)

    def _publish_zero(self) -> None:
        payload = {
            "linear": {
                "x": 0.0,
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

    def hover(self, duration: float = 1.0) -> None:
        period = 1.0 / self.publish_rate_hz
        deadline = time.monotonic() + max(duration, period)

        while time.monotonic() < deadline:
            self._publish_zero()
            time.sleep(period)

    def _run(self, duration: float = 1.0) -> str:
        self.hover(duration)
        return (
            f"Zero velocity command sent for {duration:.1f} seconds. "
            "The UAV is now hovering in place with no translation and no yaw rotation."
        )