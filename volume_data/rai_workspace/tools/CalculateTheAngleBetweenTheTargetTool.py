import math
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from geometry_msgs.msg import Point

from rai_workspace.tools.GetCurrentPositionByGpsTool import GetCurrentPositionByGpsTool
from rai_workspace.tools.GetLookingDirection import GetLookingDirectionTool



class CalculateTheAngleAndDistanceBetweenTheTargetToolInput(BaseModel):
    target_x: float = Field(description="Target x coordinate in meters (east).")
    target_y: float = Field(description="Target y coordinate in meters (north).")


class CalculateTheAngleAndDistanceBetweenTheTargetTool(BaseTool):
    connector: ROS2Connector

    name: str = "CalculateTheAngleAndDistanceBetweenTheTargetTool"
    description: str = (
        "Given a target x and y coordinate, returns the horizontal distance to it "
        "in meters and how many degrees the UAV must rotate (yaw) to face it. "
        "Positive rotation means clockwise (north -> east), negative means "
        "counter-clockwise. The rotation value can be passed directly to "
        "ChangeLookingDirection as target_looking_difference_angle, and the "
        "distance to MoveForwardTool. Altitude is ignored. "
        "Call this again after every movement to correct drift."
    )

    args_schema: Type[CalculateTheAngleAndDistanceBetweenTheTargetToolInput] = ( # type: ignore
        CalculateTheAngleAndDistanceBetweenTheTargetToolInput 
    )

    def calculate_distance_and_angle(self, target_x: float, target_y: float):
        position = GetCurrentPositionByGpsTool(connector=self.connector).get_current_point()
        heading = GetLookingDirectionTool(connector=self.connector).get_heading()

        print(f"Heading is {heading}")


        dx = target_x - position.x
        dy = target_y - position.y
        distance = math.hypot(dx, dy)

        target_bearing = math.degrees(math.atan2(dx, dy)) % 360.0

        turn = (target_bearing - heading + 180.0) % 360.0 - 180.0
        return distance, turn


    def _run(self, target_x: float, target_y: float) -> str:
        position: Point = GetCurrentPositionByGpsTool(
            connector=self.connector
        ).get_current_point()
        distance, angle_to_turn = self.calculate_distance_and_angle(target_x, target_y)

        turn_word = "clockwise" if angle_to_turn >= 0 else "counter-clockwise"

        return (
            f"Target ({target_x:.2f}, {target_y:.2f}) is {distance:.2f} m away from "
            f"the current position ({position.x:.2f}, {position.y:.2f}). "
            f"Rotate {angle_to_turn:+.1f} degrees ({turn_word}) to face it, "
            f"then move forward {distance:.2f} m."
        )