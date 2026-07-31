
from pathlib import Path
from typing import Any, List, cast

from rai.tools.ros2.simple import GetROS2ImageConfiguredTool
import rclpy
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from rai import get_llm_model
from rai.agents.langchain import (
    ReActAgent,
    ReActAgentState,
)
from rai.communication.ros2 import ROS2Connector
from rai_whoami import EmbodimentInfo

from rai_workspace.tools.WaitForSecondsTool import WaitForSecondsTool



def initialize_agent() -> Runnable[ReActAgentState, ReActAgentState]:
    rclpy.init()

    embodiment_path: Path =  Path("../embodiments/main.json")

    if embodiment_path.exists():
        print("Embodiment found.")
    else:
        raise ValueError(f"No embodiment found. The path is {embodiment_path}")
    
    embodiment_info: EmbodimentInfo = EmbodimentInfo.from_file(
       embodiment_path
    )
  

    connector = ROS2Connector(executor_type="multi_threaded", use_sim_time=True)
    tools: List[BaseTool] = [
        GetROS2ImageConfiguredTool(
                    connector=connector,
                    topic="/camera/camera/color/image_raw",
                ),
        WaitForSecondsTool(),
            # TODO: Add tools
    ]

    agent: Runnable[Any, Any] = ReActAgent(
        target_connectors={},  # empty dict, since we're using the agent in direct mode
        llm=get_llm_model("complex_model", streaming=True),
        system_prompt=embodiment_info.to_langchain(),
        tools=tools,
    ).agent
    connector.node.declare_parameter("conversion_ratio", 1.0)

    return cast(Runnable[ReActAgentState, ReActAgentState], agent)
