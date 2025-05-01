from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import asyncio
import uvicorn
import threading
import traceback
import logging
import re
import uuid

from fastapi import HTTPException
#logging.getLogger("httpcore").setLevel(logging.WARNING)
#logging.getLogger("httpx").setLevel(logging.WARNING)

#logger = logging.getLogger(__name__)

app = FastAPI()
mcp = FastMCP(name="MathMCPServer", host="0.0.0.0", port=8003)

# Store pending approvals and results
pending_approvals = {}
completed_results = {}

class MathRequest(BaseModel):
    prompt: str

class UserInputs(BaseModel):
    a: int
    b: int

@mcp.tool(
    name="multiplication",
    description="Calculates the product of two numbers."
)
async def multiply(args: UserInputs):
    print("**********************I am doing multiplicaiton*******************")
    return {"result": args.a * args.b}

@mcp.tool(
    name="addition",
    description="Calculate addition of two numbers"
)
async def add(args: UserInputs):
    print("**********************I am doing addition*******************")
    return {"result": args.a + args.b}


async def math_calculate(args: MathRequest):
    prompt = args.prompt
    task_id = str(uuid.uuid4())
    event = asyncio.Event()
    pending_approvals[task_id] = {
        "prompt": prompt,
        "event": event,
        "approved": None,
        "edited_prompt": None,
    }

    try:
        await asyncio.wait_for(event.wait(), timeout=600)
    except asyncio.TimeoutError:
        # Remove pending approval on timeout
        pending_approvals.pop(task_id, None)
        completed_results[task_id] = {"error": "Human approval timed out"}
        #logger.warning(f"Approval timed out for task {task_id}")
        return {"error": "Human approval timed out"}

    approval = pending_approvals.pop(task_id, None)
    if approval is None:
        # This should not happen, but handle gracefully
       # logger.error(f"Approval task missing for task_id {task_id}")
        return {"error": "Approval task missing"}

    if not approval.get("approved", False):
        completed_results[task_id] = {"result": "HUMAN_REJECTED"}
        return {"result": "HUMAN_REJECTED"}

    approved_prompt = approval.get("edited_prompt") or prompt

    try:
        numbers = [float(num) for num in re.findall(r"[-+]?\d*\.\d+|\d+", approved_prompt)]
        if not numbers:
            raise ValueError("No numbers found in prompt")
        result = sum(numbers)
    except Exception as e:
        completed_results[task_id] = {"error": f"Calculation failed: {str(e)}"}
        #logger.error(f"Calculation failed for task {task_id}: {e}")
        return {"error": f"Calculation failed: {str(e)}"}

    completed_results[task_id] = {"result": result}
    #logger.info(f"Calculation result for task {task_id}: {result}")
    return {"result": result}

@app.get("/pending_approvals")
async def get_pending_approvals():
    # Return list of pending tasks (id and prompt only)
    return [{"id": tid, "prompt": t["prompt"]} for tid, t in pending_approvals.items()]

@app.post("/approve/{task_id}")
async def post_approval(task_id: str, approved: bool = Form(...), edited_prompt: str = Form(None)):
    task = pending_approvals.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or already processed")
    task["approved"] = approved
    if edited_prompt:
        task["edited_prompt"] = edited_prompt
    task["event"].set()
    #logger.info(f"Task {task_id} {'approved' if approved else 'rejected'} by human")
    return {"message": f"Task {task_id} {'approved' if approved else 'rejected'}"}


def run_mcp_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mcp.run(transport="sse"))

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=run_mcp_server, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")

