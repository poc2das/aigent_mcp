# llm_client_sampling.py
import asyncio
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from mcp import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack

mcp = FastMCP(name="LLMClientSampling", host="0.0.0.0", port=8004)

approval_ui_url = "http://approval_ui:8005/sse"  # MCP server SSE endpoint

exit_stack = AsyncExitStack()
client_session: ClientSession | None = None

class ApprovalRequest(BaseModel):
    prompt: str

async def get_client_session() -> ClientSession:
    global client_session
    if client_session is None:
        transport = await exit_stack.enter_async_context(sse_client(approval_ui_url))
        client_session = await exit_stack.enter_async_context(ClientSession(*transport))
        await client_session.initialize()
    return client_session

@mcp.tool(name="prompt_approval", description="Human approval tool")
async def prompt_approval(args: ApprovalRequest):
    session = await get_client_session()
    try:
        approval_response = await session.sample(
            tool_name="human_approval",
            args={"prompt": args.prompt},
            timeout=600
        )
        return approval_response
    except asyncio.TimeoutError:
        return {"approved": False, "edited_prompt": args.prompt}
    except Exception as e:
        return {"approved": False, "edited_prompt": args.prompt, "error": str(e)}

if __name__ == "__main__":
    try:
        mcp.run(transport="sse")
    finally:
        asyncio.run(exit_stack.aclose())
