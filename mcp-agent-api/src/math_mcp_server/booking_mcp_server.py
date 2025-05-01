from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from typing import Optional
import asyncio
import uvicorn
import threading
import uuid

app = FastAPI()
templates = Jinja2Templates(directory="templates")

mcp = FastMCP(name="BookingMCPServer", host="0.0.0.0", port=8003)

# Store pending approval tasks and completed booking results
pending_approvals = {}
completed_results = {}

class UserBookingInputs(BaseModel):
    name: Optional[str] = None
    airline: Optional[str] = None
    date: Optional[str] = None
    timing: Optional[str] = None
    date: Optional[str] = None
    traveling_from: Optional[str] = None
    destination: Optional[str] = None
    credit_card: Optional[str] = None
    prompt: Optional[str] = None

@app.get("/pending_approvals")
async def get_pending_approvals():
    # Return list of pending tasks (id and prompt only)
    return [{"id": task_id, "prompt": task["prompt"]} for task_id, task in pending_approvals.items()]

@app.post("/approve/{task_id}")
async def post_approval(task_id: str, approved: bool = Form(...), edited_prompt: str = Form(None)):
    task = pending_approvals.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or already processed")

    task["approved"] = approved
    if edited_prompt:
        task["edited_prompt"] = edited_prompt

    task["event"].set()
    return {"message": f"Task {task_id} {'approved' if approved else 'rejected'}"}

@app.get("/result/{task_id}")
async def get_result(task_id: str):
    result = completed_results.get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found or not ready")
    return result

@mcp.tool(
    name="Check my calendar availability",
    description="Check my calendar availability"
)
async def calenderAvailability(args: UserBookingInputs):
    print("*******************Fetching user weekday availability *****************")
    if args.name == 'Aswini':
        return {"result": '05/08/2025'}
    else:
        return {"result": '07/09/2025'}

@mcp.tool(
    name="Get flight availability details from airlines based on my calendar availability date, travelling from and  destination",
    description="Get flight availability details from airlines based on my calendar availability date, travelling from and  destination"
)
async def getFlightAvailability(args: UserBookingInputs):
    print("************************Fetching flight from availability from airlines*****************")
    if args.date == '05/08/2025':
        return {"airline": 'Air India', "timing": '3pm', "date": "05/08/2025", "traveling_from": "Delhi", "destination": "Mumbai"}
    elif args.day == '07/09/2025':
        return {"airline": 'Indigo', "timing": '5pm', "date": "07/09/2025", "traveling_from": "Delhi", "destination": "Mumbai"}
    else:
        return {"error": "Ticket not available"}

@mcp.tool(
    name="Fetch my credit card details from my digital locker",
    description="Fetch my credit card details from my digital locker"
)
async def fetchCreditcardpaymentDetails(args: UserBookingInputs):
    print("********************Payment details confirmed*****************")
    if args.name == 'unknown':
        return {"error": 'credit card details not found or not valid'}
    return {"result": '8122-xxxx'}

@mcp.tool(
    name="After fetching all the requireds details finally book the ticket",
    description="After fetching all the requireds details finally book the ticket"
)
async def bookTicket(args: UserBookingInputs):
    print("********************************bookTicket*****************")
    
    # Clear previous state
    pending_approvals.clear()
    completed_results.clear()

    prompt = args.prompt or "No prompt provided"
    task_id = str(uuid.uuid4())
    event = asyncio.Event()

    # Store booking info to return after approval
    booking_info = {
        "airline": args.airline,
        "timing": args.timing,
        "date": args.date,
        "traveling_from": args.traveling_from,
        "destination": args.destination,
        "name": args.name,
    }

    pending_approvals[task_id] = {
        "prompt": prompt,
        "event": event,
        "approved": None,
        "edited_prompt": None,
        "booking_info": booking_info,
    }

    try:
        await asyncio.wait_for(event.wait(), timeout=600)  # Wait up to 10 minutes
    except asyncio.TimeoutError:
        pending_approvals.pop(task_id, None)
        completed_results[task_id] = {"error": "Human approval timed out"}
        return {"error": "Human approval timed out"}

    approval = pending_approvals.pop(task_id)

    if not approval.get("approved", False):
        completed_results[task_id] = {"error": "Prompt rejected by human"}
        return {"result": "HUMAN_REJECTED"}

    # Save booking info to completed_results for UI retrieval
    completed_results[task_id] = {
        "result": "Booking confirmed",
        **approval.get("booking_info", {})
    }

    return completed_results[task_id]

def run_mcp_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mcp.run(transport="sse"))

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=run_mcp_server, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")
