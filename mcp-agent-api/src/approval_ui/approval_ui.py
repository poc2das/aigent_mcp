from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from mcp.server.fastmcp import FastMCP
import asyncio
from uuid import uuid4

app = FastAPI()
templates = Jinja2Templates(directory="templates")

mcp = FastMCP(name="ApprovalUI")

approval_sessions = {}

@mcp.tool(name="human_approval", description="Human approval UI")
async def human_approval(args: dict):
    session_id = str(uuid4())
    event = asyncio.Event()

    approval_sessions[session_id] = {
        "prompt": args.get("prompt", ""),
        "approved": False,
        "edited_prompt": args.get("prompt", ""),
        "event": event
    }

    await event.wait()

    session = approval_sessions.pop(session_id)
    return {
        "approved": session["approved"],
        "edited_prompt": session["edited_prompt"]
    }

@app.get("/", response_class=HTMLResponse)
async def approval_queue(request: Request):
    return templates.TemplateResponse("queue.html", {"request": request, "sessions": approval_sessions})

@app.get("/approve/{session_id}", response_class=HTMLResponse)
async def approve_form(request: Request, session_id: str):
    session = approval_sessions.get(session_id)
    if not session:
        return HTMLResponse("Session not found", status_code=404)
    return templates.TemplateResponse("approve.html", {
        "request": request,
        "session_id": session_id,
        "prompt": session["prompt"],
        "edited_prompt": session["edited_prompt"]
    })

@app.post("/approve/{session_id}")
async def approve_post(session_id: str, approved: str = Form(...), edited_prompt: str = Form(...)):
    session = approval_sessions.get(session_id)
    if not session:
        return RedirectResponse("/", status_code=303)
    session["approved"] = (approved == "yes")
    session["edited_prompt"] = edited_prompt
    session["event"].set()
    return RedirectResponse("/", status_code=303)

app.mount("/mcp", mcp)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
