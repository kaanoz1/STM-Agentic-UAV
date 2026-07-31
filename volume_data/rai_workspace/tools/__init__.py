import time
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class WaitForSecondsToolInput(BaseModel):
    """Input for the WaitForSecondsTool tool."""

    seconds: int = Field(..., description="The number of seconds to wait")


class WaitForSecondsTool(BaseTool):
    """Wait for a specified number of seconds"""

    name: str = "WaitForSecondsTool"
    description: str = (
        "A tool for waiting. "
        "Useful for pausing execution for a specified number of seconds. "
        "Input should be the number of seconds to wait."
        "Maximum allowed time is 10 seconds"
    )

    args_schema: Type[WaitForSecondsToolInput] = WaitForSecondsToolInput # type: ignore

    def _run(self, seconds: int) -> str:
        """Waits for the specified number of seconds."""
        if seconds > 10:
            seconds = 10
        time.sleep(seconds)
        return f"Waited for {seconds} seconds."
