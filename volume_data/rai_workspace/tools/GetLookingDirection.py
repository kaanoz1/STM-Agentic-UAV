import math
from typing import Tuple

from langchain_core.tools import BaseTool
from pydantic import Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from geometry_msgs.msg import Vector3Stamped, Vector3
from webots_ros2_msgs.msg import FloatStamped


_DIRECTIONS: Tuple[Tuple[str, float], ...] = (
    ("north", 0.0),
    ("north-east", 45.0),
    ("east", 90.0),
    ("south-east", 135.0),
    ("south", 180.0),
    ("south-west", 225.0),
    ("west", 270.0),
    ("north-west", 315.0),
)


def _bearing_from_north_vector(vector: Vector3) -> float:
    """Heading in degrees clockwise from north (0=N, 90=E, 180=S, 270=W)."""
    return math.degrees(math.atan2(vector.x, -vector.y)) % 360.0


def _closest_direction(bearing: float) -> Tuple[str, float]:
    """Nearest of the 8 compass directions, plus signed offset in (-22.5, +22.5]."""
    index = int(round(bearing / 45.0)) % 8
    name, reference = _DIRECTIONS[index]
    offset = (bearing - reference + 180.0) % 360.0 - 180.0
    return name, offset


class GetLookingDirectionTool(BaseTool):
    connector: ROS2Connector

    name: str = "GetLookingDirectionTool"
    description: str = (
        "Gets the current heading of the UAV by listening to the compass topic. "
        "Returns the closest compass direction (north, north-east, east, ...), "
        "the signed offset from that direction in degrees, and the absolute "
        "bearing measured clockwise from north."
    )

    north_vector_topic_name: str = Field(default="/Mavic_2_PRO/compass/north_vector")
    bearing_topic_name: str = Field(default="/Mavic_2_PRO/compass/bearing")

    def get_north_vector(self) -> Vector3:
        message: ROS2Message = self.connector.receive_message(
            self.north_vector_topic_name, timeout_sec=3
        )
        if not isinstance(message.payload, Vector3Stamped):
            raise ValueError(f"Unsupported message type: {type(message.payload)}")
        return message.payload.vector

    def get_bearing(self) -> float:
        message: ROS2Message = self.connector.receive_message(
                    self.bearing_topic_name, timeout_sec=3
                )
        if not isinstance(message.payload, FloatStamped):
            raise ValueError(f"Unsupported message type: {type(message.payload)}")
        return -message.payload.data

    def get_bearing_from_north(self) -> float:
        return _bearing_from_north_vector(self.get_north_vector())

    def is_looking_north(self, tolerance_deg: float = 5.0) -> bool:
        bearing = self.get_bearing_from_north()
        return min(bearing, 360.0 - bearing) <= tolerance_deg


    def get_heading(self) -> float:
        """Heading in degrees clockwise from north. 0=N, 90=E, 180=S, 270=W."""
        v = self.get_north_vector()
        return (math.degrees(math.atan2(v.y, v.x))) % 360.0


    def _run(self, tolerance: float = 5.0) -> str:
        bearing = self.get_bearing_from_north()
        direction, offset = _closest_direction(bearing)

        if abs(offset) <= tolerance:
            alignment = f"aligned with {direction}"
        else:
            turn = "clockwise" if offset > 0 else "counter-clockwise"
            alignment = f"{abs(offset):.1f} degrees {turn} of {direction}"

        return (
            f"The UAV is facing {direction} ({alignment}). "
            f"Bearing from north: {bearing:.1f} degrees clockwise. "
            f"Offset from {direction}: {offset:+.1f} degrees."
        )