
from pathlib import Path
from typing import Any, List, cast

import rclpy
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from rai.agents.langchain import (
    ReActAgent,
    ReActAgentState,
)
from rai.communication.ros2 import ROS2Connector
from rai_whoami import EmbodimentInfo
from rai_workspace.tools.WaitForSecondsTool import WaitForSecondsTool
from rai_workspace.tools.GetROS2ImageConfiguredTool import GetROS2ImageConfiguredTool

from function_def_get_llm_model import get_llm_model

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
        llm=get_llm_model(),
        system_prompt=embodiment_info.to_langchain(),
        tools=tools,
    ).agent
    connector.node.declare_parameter("conversion_ratio", 1.0)

    return cast(Runnable[ReActAgentState, ReActAgentState], agent)
