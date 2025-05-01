from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
import asyncio
import uvicorn
import threading
import uuid

pending_approvals = {}
completed_results = {}

app = FastAPI()
templates = Jinja2Templates(directory="templates")
mcp = FastMCP(name="BookingMCPServer", host="0.0.0.0", port=8003)

class UserBookingInputs(BaseModel):
    name: str
    dob: str = None
    address: str = None
    airline: str = None
    day: str = None
    timing: str = None
    date: str = None
    traveling_from: str = None
    destination: str = None
    prompt: str = None

@app.get("/pending_approvals")
async def get_pending_approvals():
    return [
        {"id": task_id, "prompt": task["prompt"]}
        for task_id, task in pending_approvals.items()
    ]

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
    name="Get my calendar availability",
    description="Get the weekday and time availability in my Teams calendar"
)
async def calenderAvailability(args: UserBookingInputs):
    if args.name == 'Aswini':
        return {"result": 'wednesday'}
    else:
        return {"result": 'friday'}

@mcp.tool(
    name="Get flight itinerary availability from airlines",
    description="Get flight options for a given day and route"
)
async def getFlightAvailability(args: UserBookingInputs):
    if args.day == 'wednesday':
        return {"airline": 'Air India', "timing": '3pm', "date": "05/20/2025", "traveling_from":"Delhi", "destination": "Mumbai"}
    elif args.day == 'friday':
        return {"airline": 'Indigo', "timing": '5pm', "date": "05/20/2025", "traveling_from":"Delhi", "destination": "Mumbai"}
    else:
        return {"error": "Ticket not available"}

@mcp.tool(
    name="Fetch my credit card details from digital locker",
    description="Fetch credit card details for payment"
)
async def fetchCreditcardpaymentDetails(args: UserBookingInputs):
    if args.name == 'unknown':
        return {"error": 'credit card details not found or not valid'}
    return {"result": 'Visa credit card xxxx-8122'}

@mcp.tool(
    name="Book my itinerary",
    description="Book the itinerary with the specified airlines; requires human approval"
)
async def bookItinerary(args: UserBookingInputs):
    # Human-in-the-loop approval
    prompt = args.prompt or f"Book flight for {args.name} from {args.traveling_from} to {args.destination} on {args.date} with {args.airline} at {args.timing}"
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
        pending_approvals.pop(task_id, None)
        completed_results[task_id] = {"error": "Human approval timed out"}
        return {"error": "Human approval timed out"}
    approval = pending_approvals.pop(task_id)
    if not approval.get("approved", False):
        completed_results[task_id] = {"error": "Prompt rejected by human"}
        return {"result": "HUMAN_REJECTED"}
    approved_prompt = approval.get("edited_prompt") or prompt
    completed_results[task_id] = {"result": 'Booking confirmed'}
    return {"result": 'Booking confirmed'}

def run_mcp_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mcp.run(transport="sse"))

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=run_mcp_server, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")
