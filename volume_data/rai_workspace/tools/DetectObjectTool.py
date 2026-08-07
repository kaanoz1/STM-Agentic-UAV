import math
import threading
from typing import Any, Type

import numpy as np
import torch
from cv_bridge import CvBridge
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from rai.communication.ros2.connectors.ros2_connector import ROS2Connector
from rai.communication.ros2.messages import ROS2Message
from sensor_msgs.msg import CameraInfo, CompressedImage, Image

MODEL_PATH = "/rai/rai_workspace/models/yolov8s-world.pt"

_model = None
_model_classes: list[str] | None = None
_model_lock = threading.Lock()


def _get_model():
    """Load the YOLO-World model once and reuse it across tool calls."""
    global _model
    if _model is None:
        from ultralytics import YOLOWorld

        _model = YOLOWorld(MODEL_PATH)
    return _model


_SYNONYMS = {
    "person": ["person", "human", "man", "woman", "pedestrian"],
    "car": ["car", "automobile", "vehicle", "sedan"],
}

def _expand_label(label: str) -> list[str]:
    """Return the label plus any known synonyms, deduplicated, label-first."""
    key = label.strip().lower()
    extras = _SYNONYMS.get(key, [])
    seen = []
    for candidate in [label, *extras]:
        if candidate not in seen:
            seen.append(candidate)
    return seen


def _prepare_model(labels: list[str]):
    """Return the shared model configured for `labels`, reusing the last setup."""
    global _model_classes
    with _model_lock:
        model = _get_model()
        if _model_classes != labels:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.model.cpu()  # type: ignore
            model.set_classes(labels)
            model.model.to(device)  # type: ignore
            _model_classes = labels
        return model


class DetectObjectToolInput(BaseModel):
    label: str = Field(
        description=(
            "What to look for, in plain English lowercase, for example "
            "'cardboard box', 'blue car', 'manhole cover', 'windmill'. "
            "Use a short noun phrase describing the object, not a sentence."
            "Internally this also checks a few common synonyms of your label (for example "
            "'person' also checks 'human' and 'pedestrian'), so you do not need to retry "
            "with different wordings yourself if the first attempt finds nothing."
        ),
    )
    confidence: float = Field(
        default=0.15,
        description="Minimum detection confidence between 0 and 1.",
    )


class DetectObjectTool(BaseTool):
    connector: ROS2Connector

    name: str = "DetectObjectTool"
    description: str = (
        "Looks for a named object in the UAV's current camera view and returns where "
        "it appears in the image. "
        "A plain 'find X' or 'is there an X' request only needs GetCameraImage -- look "
        "at the image and describe what you see in words. Call this tool only when the "
        "task requires a precise position: facing the object, computing its "
        "coordinates, or moving towards it. "
        "Give it a short description of the object such as 'cardboard box' or 'blue car'. "
        "It captures a fresh camera frame by itself, so you do not pass an image to it. "
        "Returns, for each match: the pixel coordinates of the object's center, how "
        "large it appears, and the horizontal angle offset in degrees between the UAV's "
        "current heading and the object. A negative offset means the object is to the "
        "left, positive means it is to the right. That offset can be passed directly to "
        "ChangeLookingDirection to turn and face the object. "
        "Call this at most once per hover position. If it finds a match, stop -- do not "
        "call it again unless you are about to navigate towards the object and need a "
        "fresh measurement after moving."
    )
    args_schema: Type[DetectObjectToolInput] = DetectObjectToolInput  # type: ignore

    image_topic_name: str = Field(default="/Mavic_2_PRO/camera/image_color")
    camera_info_topic_name: str = Field(default="/Mavic_2_PRO/camera/camera_info")
    timeout_sec: float = Field(default=5.0)
    max_detections: int = Field(default=5)


    def _capture_frame(self) -> np.ndarray:
        message: ROS2Message = self.connector.receive_message(
            self.image_topic_name, timeout_sec=self.timeout_sec
        )
        payload = message.payload
        bridge = CvBridge()

        if isinstance(payload, Image):
            frame = bridge.imgmsg_to_cv2(payload, desired_encoding="passthrough")
        elif isinstance(payload, CompressedImage):
            frame = bridge.compressed_imgmsg_to_cv2(payload, desired_encoding="passthrough")
        else:
            raise ValueError(f"Unsupported message type: {type(payload)}")

        # The Webots camera publishes bgra8; drop the alpha channel.
        if frame.ndim == 3 and frame.shape[2] == 4:
            frame = frame[:, :, :3]
        return np.ascontiguousarray(frame)

    def _get_intrinsics(self, width: int, height: int) -> tuple[float, float, float, float]:
        """Returns (fx, fy, cx, cy). Falls back to a 60 degree horizontal FOV estimate."""
        try:
            message: ROS2Message = self.connector.receive_message(
                self.camera_info_topic_name, timeout_sec=self.timeout_sec
            )
            if isinstance(message.payload, CameraInfo):
                fx = float(message.payload.k[0])
                fy = float(message.payload.k[4])
                cx = float(message.payload.k[2])
                cy = float(message.payload.k[5])
                if fx > 0.0 and fy > 0.0:
                    return fx, fy, cx, cy
        except Exception:
            pass
        
        fov = math.radians(60.0)
        fx_fallback = (width / 2.0) / math.tan(fov / 2.0)
        return fx_fallback, fx_fallback, width / 2.0, height / 2.0    

    def detect(self, label: str, confidence: float = 0.15) -> list[dict[str, Any]]:
        labels = _expand_label(label)
        frame = self._capture_frame()
        height, width = frame.shape[:2]
        fx, fy, cx, cy = self._get_intrinsics(width, height)

        model = _prepare_model(labels)
        results = model.predict(frame, conf=confidence, verbose=False)

        detections: list[dict[str, Any]] = []
        for result in results:
            for box in result.boxes:  # type: ignore
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                center_x = (x1 + x2) / 2.0
                center_y = (y1 + y2) / 2.0
                class_id = int(box.cls[0])
                matched_label = labels[class_id] if class_id < len(labels) else label

                detections.append(
                    {
                        "center_x": center_x,
                        "center_y": center_y,
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "area_ratio": ((x2 - x1) * (y2 - y1)) / (width * height),
                        "confidence": float(box.conf[0]),
                        "matched_label": matched_label,
                        "angle_offset": math.degrees(math.atan2(center_x - cx, fx)),
                        "fy": fy,
                        "cy": cy,
                        "image_width": width,
                        "image_height": height,
                    }
                )

        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections[: self.max_detections]

    def _run(self, label: str, confidence: float = 0.15) -> str:
        try:
            detections = self.detect(label, confidence)
        except Exception as error:
            return (
                f"Detection failed: {error}. The camera frame could not be captured or "
                "the model could not run. Make sure the UAV is airborne and try again."
            )

        if not detections:
            return (
                f"No '{label}' found in the current camera view. "
                "The object may be outside the field of view, too far away, or too "
                "small to recognise. Rotate to scan a different direction, or descend "
                "to get a closer view, then try again."
            )

        lines = [f"Found {len(detections)} candidate(s) for '{label}':"]
        for index, d in enumerate(detections, start=1):
            side = "right" if d["angle_offset"] > 0 else "left"
            lines.append(
                f"{index}. center pixel ({d['center_x']:.0f}, {d['center_y']:.0f}) "
                f"in a {d['image_width']}x{d['image_height']} image, "
                f"box {d['width']:.0f}x{d['height']:.0f} px "
                f"({d['area_ratio'] * 100:.1f}% of the frame), "
                f"confidence {d['confidence']:.2f}, "
                f"horizontal offset {d['angle_offset']:+.1f} degrees to the {side}."
            )

        best = detections[0]
        lines.append(
            f"To face the best match, rotate {best['angle_offset']:+.1f} degrees with "
            "ChangeLookingDirection, then hover and detect again to confirm the object "
            "is centered."
        )
        return "\n".join(lines)