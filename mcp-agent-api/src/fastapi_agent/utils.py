import re
from pydantic_ai.agent import AgentRunResult

class CustomFormatter:
    def __call__(self, result: AgentRunResult) -> str:
        output = result.data
        print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

        # Match any <tool-use> containing an empty object or tool_calls: []
        pattern = re.compile(
            r"<tool-use>\s*\{\s*(\"tool_calls\"\s*:\s*\[\s*\])?\s*\}\s*</tool-use>", re.DOTALL
        )

        if pattern.search(output):
            output = pattern.sub(
                "[No tool was available on the MCP math server for this operation, so I calculated it myself.]", 
                output
            )
           
        return output
