import math
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from sensor_msgs.msg import LaserScan

from rai_workspace.tools.GetCurrentPositionByGpsTool import GetCurrentPositionByGpsTool


class CheckObstacleClearanceToolInput(BaseModel):
    relative_bearing: float = Field(
        default=0.0,
        description=(
            "Direction to check, in degrees relative to the UAV's current heading. "
            "0 means straight ahead. Use the angle_offset returned by DetectObjectTool."
        ),
    )
    target_distance: float = Field(
        description=(
            "Horizontal distance to the object you intend to fly over, in meters. "
            "Only obstacles at roughly this distance are considered; anything much "
            "further away is ignored as irrelevant background."
        ),
    )


class CheckObstacleClearanceTool(BaseTool):
    connector: ROS2Connector

    name: str = "CheckObstacleClearanceTool"
    description: str = (
        "Checks whether the UAV is currently flying above the top of an object, using "
        "the 360 degree lidar. The lidar scans a flat horizontal plane at the UAV's own "
        "altitude, so an object disappears from the scan exactly when the UAV has risen "
        "above it. "
        "Call this before flying over an object whose height you do not know, such as a "
        "house, a tree or a windmill. Pass relative_bearing as the angle_offset that "
        "DetectObjectTool returned, and target_distance as the measured horizontal "
        "distance to the object. "
        "This tool only reports what the lidar sees at the current altitude -- it does "
        "not move the UAV. If it reports that the direction is still blocked, climb with "
        "ChangeAltitudeTool, hover, and call this tool again. Repeat until it reports "
        "clear. Do not fly over the object until it does."
    )

    args_schema: Type[CheckObstacleClearanceToolInput] = CheckObstacleClearanceToolInput  # type: ignore

    scan_topic_name: str = Field(default="/Mavic_2_PRO/scan")
    window_deg: float = Field(
        default=20.0,
        description="Angular window around the bearing to consider.",
    )
    distance_margin: float = Field(
        default=2.0,
        description="Half-width of the distance band around target_distance.",
    )
    timeout_sec: float = Field(default=5.0)

    def _read_scan(self) -> LaserScan:
        message: ROS2Message = self.connector.receive_message(
            self.scan_topic_name, timeout_sec=self.timeout_sec
        )
        if not isinstance(message.payload, LaserScan):
            raise ValueError(f"Unsupported message type: {type(message.payload)}")
        return message.payload

    def _closest_range_at(self, scan: LaserScan, bearing_deg: float) -> Optional[float]:
        """Smallest valid range within a window around the given relative bearing."""
        if scan.angle_increment == 0.0:
            return None

        target = math.radians(bearing_deg)
        center = int(round((target - scan.angle_min) / scan.angle_increment))
        half = max(1, int(math.radians(self.window_deg / 2.0) / scan.angle_increment))

        total = len(scan.ranges)
        candidates = []
        for offset in range(-half, half + 1):
            value = scan.ranges[(center + offset) % total]
            if math.isfinite(value) and scan.range_min <= value <= scan.range_max:
                candidates.append(value)

        return min(candidates) if candidates else None

    def _run(self, relative_bearing: float = 0.0, target_distance: float = 5.0) -> str:
        altitude = GetCurrentPositionByGpsTool(
            connector=self.connector
        ).get_current_point().z

        try:
            scan = self._read_scan()
        except Exception as error:
            return (
                f"Could not read the lidar: {error}. Clearance could not be verified, "
                "so do not fly over the object."
            )

        blocking = self._closest_range_at(scan, relative_bearing)

        if blocking is not None and blocking < 2.0:
            return (
                f"TOO CLOSE at {altitude:.2f} m altitude. The lidar sees an obstacle only "
                f"{blocking:.2f} m away in that direction, which is too close to climb "
                f"safely. Back away first with MovingForwardTool using a negative "
                f"distance of about {2.5 - blocking:.1f} m, hover, then check clearance "
                "again."
            )

        near = max(0.2, target_distance - self.distance_margin)
        far = target_distance + self.distance_margin

        if blocking is None:
            return (
                f"CLEAR at {altitude:.2f} m altitude. The lidar detects nothing within "
                f"{self.window_deg:.0f} degrees of that bearing, so the UAV is above "
                "anything in that direction and may fly over it."
            )

        if not (near <= blocking <= far):
            return (
                f"CLEAR at {altitude:.2f} m altitude. The nearest lidar return in that "
                f"direction is at {blocking:.2f} m, outside the {near:.1f}-{far:.1f} m "
                f"band around the target at {target_distance:.1f} m, so it is background "
                "rather than the object being flown over."
            )

        return (
            f"BLOCKED at {altitude:.2f} m altitude. The lidar sees an obstacle at "
            f"{blocking:.2f} m in that direction, which falls within the "
            f"{near:.1f}-{far:.1f} m band around the target. The UAV is still below the "
            f"top of that object. Climb with ChangeAltitudeTool to roughly "
            f"{altitude + 2.0:.1f} m, hover, then call this tool again to re-check."
        )