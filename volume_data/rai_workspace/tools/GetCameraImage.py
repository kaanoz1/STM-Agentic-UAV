

from typing import Any, Literal, Tuple, Type
from cv_bridge import CvBridge
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from rai.messages.artifacts import MultimodalArtifact
from rai.messages import preprocess_image
from rai.tools.ros2.base import BaseROS2Tool

from sensor_msgs.msg import CompressedImage, Image

class GetROS2ImageToolInput(BaseModel):
    topic: str = Field(..., description="The topic to receive the image from")
    timeout_sec: float = Field(1.0, description="The timeout in seconds")




class GetROS2ImageTool(BaseROS2Tool):
    connector: ROS2Connector
    name: str = "GetROS2ImageTool"
    description: str = "Get an image from a ROS2 topic"
    args_schema: Type[GetROS2ImageToolInput] = GetROS2ImageToolInput # type: ignore
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    def _run(
        self, topic: str, timeout_sec: float = 1.0
    ) -> Tuple[str, MultimodalArtifact]:
        if not self.is_readable(topic):
            raise ValueError(f"Topic {topic} is not readable")
        message: ROS2Message = self.connector.receive_message(topic, timeout_sec=timeout_sec)
        msg_type = type(message.payload)
        if msg_type == Image:
            image = CvBridge().imgmsg_to_cv2(  # type: ignore
                message.payload, desired_encoding="rgb8"
            )
        elif msg_type == CompressedImage:
            image = CvBridge().compressed_imgmsg_to_cv2(  # type: ignore
                message.payload, desired_encoding="rgb8"
            )
        else:
            raise ValueError(
                f"Unsupported message type: {message.metadata['msg_type']}"
            )
        return "Photo captured", MultimodalArtifact(
            images=[preprocess_image(image)]
        )  # type: ignore


class GetCameraImage(BaseROS2Tool):
    name: str = "GetCameraImage"
    description: str = "Get the current image from the camera"
    response_format: Literal["content", "content_and_artifact"] = "content_and_artifact"

    topic: str = Field(..., description="The topic to get the image from")
    timeout_sec: float = Field(default=5.0, description="The timeout in seconds")

    def model_post_init(self, __context: Any) -> None:
        if not self.is_readable(topic=self.topic):
            raise ValueError(f"Bad configuration: topic {self.topic} is not readable")

    def _run(self) -> Any:
        tool = GetROS2ImageTool(
            connector=self.connector,
        )
        return tool._run(topic=self.topic, timeout_sec=self.timeout_sec)