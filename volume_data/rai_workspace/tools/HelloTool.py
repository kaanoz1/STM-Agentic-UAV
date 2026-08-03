from langchain_core.tools import BaseTool

class SayHelloTool(BaseTool):
    name: str = "SayHelloTool"
    description: str = (
        "A tool for saying Hello to the user"
    )

    def _run(self) -> str:
        return f"I said Hello. That is done"
