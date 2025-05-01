import os
import logging
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP
import json
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)

# Set your Groq API key and base URL
os.environ["GROQ_API_KEY"] = ""
os.environ["GROQ_API_BASE_URL"] = "https://api.groq.com/openai/v1"

# System prompt definition
system_prompt = """
You are a helpful assistant.

You can use external tools to perform **either addition or multiplication**, based on the user's request.

Only call one tool per user query — either "addition" or "multiplication", never both.

When you need to call a tool, respond using valid JSON **inside <tool-use> tags**, like this:

<tool-use>
{"tool_calls":[{"tool_name":"addition","args":{"a":2,"b":4}}]}
</tool-use>

Never return empty tool_calls lists. If no valid tool is required, do not use <tool-use> tags.

If the user request doesn't match any tool, respond with a plain JSON result like:

{"result": "External tool was not available to perform this action."}

If a tool provides a JSON response (e.g., {"result": 6}), return ONLY that as the final output — **without wrapping it in <tool-use> tags**.

You must always return a valid JSON object — either as a final result or wrapped in <tool-use> for tool calls. Never return plain text, and never wrap a result inside <tool-use> unless it is an actual tool call.

"""

# FastAPI app setup
app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

# URL for MCP server hosting math tools
MATH_MCP_SERVER_URL = "http://math_mcp_server:8003/sse"

# MCP Server integration
mcp_server = MCPServerHTTP(url=MATH_MCP_SERVER_URL)

# Agent setup with the system prompt and MCP server
agent = Agent(
    model="groq:llama3-8b-8192",  # Specify the Groq model
    mcp_servers=[mcp_server],  # Attach MCP servers for tool calls
    system_prompt=system_prompt  # Enforcing the single tool call rule
)

@app.post("/analyze")
async def analyze_prompt(req: PromptRequest):
    try:
        async with agent.run_mcp_servers():
            response = await agent.run(req.prompt)
           # Parse the output JSON string
            print("^^^^^^^^^^^^^^^^^^response^^^^^^^^^^^^^^^^",response)
           # output_json = json.loads(response.output) if isinstance(response.output, str) else response.output
            # Extract the 'result' value
           # numeric_result = output_json.get("result")
           # return {"result": numeric_result}
            return {"result": response.output}
            
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Groq API request timed out")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
