from langchain_core.tools import BaseTool
from pydantic import Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from geometry_msgs.msg import PointStamped, Point


class GetCurrentPositionByGpsTool(BaseTool):
    connector: ROS2Connector

    name: str = "GetCurrentPositionByGpsTool"
    description: str = (
            "Gets the current position by listening the gps topic"
            "Returns 3D point: x, y and z."
        )


    gps_topic_name: str = Field(default="/Mavic_2_PRO/gps")

    def get_current_point(self) -> Point:
        message: ROS2Message = self.connector.receive_message(self.gps_topic_name, timeout_sec=3)
        
        if not isinstance(message.payload, PointStamped):
            raise ValueError(f"Unsupported message type: {type(message.payload)}")
        return message.payload.point;


    def _run(self) -> str:

        point = self.get_current_point()
        
        x = point.x
        y = point.y
        z = point.z

        return f"The UAV located on (x, y, z) = ({x}, {y}, {z}) "