
from pathlib import Path
from typing import Any, List, cast

from rai_workspace.tools.CalculateTheAngleBetweenTheTargetTool import CalculateTheAngleAndDistanceBetweenTheTargetTool
from rai_workspace.tools.ChangeLookingDirection import ChangeLookingDirection
from rai_workspace.tools.GetCurrentPositionByGpsTool import GetCurrentPositionByGpsTool
from rai_workspace.tools.GetLookingDirection import GetLookingDirectionTool
from rai_workspace.tools.HelloTool import SayHelloTool
from rai_workspace.tools.HoverWithNoSwayTool import HoverWithNoSwayTool
import rclpy
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from rai.agents.langchain import (
    ReActAgent,
    ReActAgentState,
)
from rai_workspace.tools.GetObjectPositionTool import GetObjectPositionTool
from rai.communication.ros2 import ROS2Connector
from rai_whoami import EmbodimentInfo
from rai_workspace.tools.WaitForSecondsTool import WaitForSecondsTool
from rai_workspace.tools.GetCameraImage import GetCameraImage

from rai_workspace.agent.function_def_get_llm_model import get_llm_model
from rai_workspace.tools.ChangeAltitudeTool import ChangeAltitudeTool
from rai_workspace.tools.MovingForwardTool import MovingForwardTool
from rai_workspace.tools.DetectObjectTool import DetectObjectTool

def initialize_agent() -> Runnable[ReActAgentState, ReActAgentState]:
    if not rclpy.ok():
        rclpy.init()

    embodiment_path: Path =  Path("rai_workspace/embodiments/main.json")

    if embodiment_path.exists():
        print("Embodiment found.")
    else:
        raise ValueError(f"No embodiment found. The path is {embodiment_path}")
    
    embodiment_info: EmbodimentInfo = EmbodimentInfo.from_file(
       embodiment_path
    )
  

    connector = ROS2Connector(executor_type="multi_threaded", use_sim_time=True)

    
    tools: List[BaseTool] = [
        CalculateTheAngleAndDistanceBetweenTheTargetTool(connector=connector),
        ChangeAltitudeTool(connector=connector),
        ChangeLookingDirection(connector=connector),
        DetectObjectTool(connector=connector),
        GetCameraImage(
                    connector=connector,
                    topic="/Mavic_2_PRO/camera/image_color",
                ),
        GetCurrentPositionByGpsTool(connector=connector),
        GetLookingDirectionTool(connector=connector),
        GetObjectPositionTool(connector=connector),
        # SayHelloTool(),
        HoverWithNoSwayTool(connector=connector),
        MovingForwardTool(connector=connector),
        # WaitForSecondsTool(),
    ]

    agent: Runnable[Any, Any] = ReActAgent(
        target_connectors={}, 
        llm=get_llm_model(),
        system_prompt=embodiment_info.to_langchain(),
        tools=tools,
    ).agent



    return cast(Runnable[ReActAgentState, ReActAgentState], agent)
























    # connector.node.declare_parameter("conversion_ratio", 1.0)
