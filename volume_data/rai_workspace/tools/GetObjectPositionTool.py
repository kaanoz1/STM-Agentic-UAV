import math
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from geometry_msgs.msg import Point

from rai_workspace.tools.DetectObjectTool import DetectObjectTool
from rai_workspace.tools.GetCurrentPositionByGpsTool import GetCurrentPositionByGpsTool
from rai_workspace.tools.GetLookingDirection import GetLookingDirectionTool


class GetObjectPositionToolInput(BaseModel):
    label: str = Field(
        description=(
            "What to look for, in plain English lowercase, for example "
            "'cardboard box', 'blue car', 'manhole cover'. Same format as "
            "DetectObjectTool."
        ),
    )
    confidence: float = Field(
        default=0.1,
        description="Minimum detection confidence between 0 and 1.",
    )


class GetObjectPositionTool(BaseTool):
    connector: ROS2Connector

    name: str = "GetObjectPositionTool"
    description: str = (
        "Estimates the world x, y coordinate of a named object that is resting on "
        "the ground, using the current camera view. It detects the object, measures "
        "how far below the horizon it appears, and combines that with the UAV's "
        "altitude to compute distance, then combines the distance with the UAV's "
        "heading to compute the object's x, y position. "
        "Returns target_x and target_y, which you should pass directly to "
        "CalculateTheAngleAndDistanceBetweenTheTargetTool to plan the rotate and "
        "move sequence towards the object. "
        "This only works for objects on the ground; it will refuse to estimate a "
        "position for something above the horizon line, such as a bird or a rooftop "
        "object. The UAV must be hovering and stable when this is called."
    )

    args_schema: Type[GetObjectPositionToolInput] = GetObjectPositionToolInput  # type: ignore

    min_vertical_angle_deg: float = Field(
        default=1.0,
        description=(
            "Minimum downward angle to the object before a distance estimate is "
            "trusted. Below this, the object is too close to the horizon and the "
            "distance would blow up or be unreliable."
        ),
    )

    def _run(self, label: str, confidence: float = 0.15) -> str:
        detector = DetectObjectTool(connector=self.connector)

        try:
            detections = detector.detect(label, confidence)
        except Exception as error:
            return (
                f"Detection failed: {error}. The camera frame could not be captured "
                "or the model could not run."
            )

        if not detections:
            return (
                f"No '{label}' found in the current camera view, so its position "
                "cannot be estimated. Locate it first with DetectObjectTool or "
                "GetCameraImage."
            )

        best = detections[0]

        # Downward angle from the optical axis to the bottom of the bounding box.
        # The camera looks straight ahead (no pitch), so this angle is measured
        # directly against the horizon.
        vertical_angle = math.degrees(
            math.atan2(best["y2"] - best["cy"], best["fy"])
        )

        if vertical_angle <= self.min_vertical_angle_deg:
            return (
                f"'{label}' is too close to the horizon in the frame (vertical angle "
                f"{vertical_angle:.1f} degrees) to estimate a reliable distance. "
                "This usually means the object is far away, elevated off the ground, "
                "or the UAV needs to descend for a steeper viewing angle. Try "
                "descending a little and detecting again."
            )

        position: Point = GetCurrentPositionByGpsTool(
            connector=self.connector
        ).get_current_point()
        heading = GetLookingDirectionTool(connector=self.connector).get_heading()

        distance = position.z / math.tan(math.radians(vertical_angle))
        bearing = (heading + best["angle_offset"]) % 360.0
        bearing_rad = math.radians(bearing)

        target_x = position.x + distance * math.sin(bearing_rad)
        target_y = position.y + distance * math.cos(bearing_rad)

        return (
            f"Estimated position of '{label}': target_x={target_x:.2f}, "
            f"target_y={target_y:.2f} (distance {distance:.2f} m, bearing "
            f"{bearing:.1f} degrees from north, computed from UAV altitude "
            f"{position.z:.2f} m and vertical angle {vertical_angle:.1f} degrees). "
            "This estimate assumes the object is resting on the ground. "
            "Pass target_x and target_y to CalculateTheAngleAndDistanceBetweenThe"
            "TargetTool to get the rotation angle and travel distance, then rotate "
            "with ChangeLookingDirection and move with MovingForwardTool."
        )