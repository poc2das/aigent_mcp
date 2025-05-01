import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP
import traceback
import json
import logging
import asyncio

import os
import re
import json
import traceback
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

import logging

logging.basicConfig(level=logging.DEBUG)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.DEBUG)

# Set your Groq API key and base URL (replace with your actual keys)
os.environ["GROQ_API_KEY"] = "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"
os.environ["GROQ_API_BASE_URL"] = "https://api.groq.com/openai/v1"

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

BOOKING_MCP_SERVER_URL = "http://booking_mcp_server:8003/sse"

system_prompt123 = """
You are a flight booking assistant.
You have access to tools for:
- Checking calendar availability
- Get flight itinerary availability from airlines
- Fetch my credit card details from digital locker
- Booking flights

Ask the user for any missing required details (name, traveling from, destination).
Always call the appropriate tool for each step.
If information is missing, ask for it. Do not assume values.
After booking, wait for human approval before confirming.
If any error occurs, return a JSON object with an "error" key describing the issue.
"""

system_prompt_old = """
You are a flight booking assistant. You have access to the following tools:

1. Check my calendar availability
   - Input parameter: JSON object with key "args"
   - "args" contains:
       - name (string, required)
   - Example call:
     {"args": {"name": "Aswini"}}


2. Get flight availability details from airlines based on my calendar availability date, travelling from and  destination
   - Input parameter: JSON object with key "args"
   - "args" contains:
       - date (string, required)
       - travelling_from (string, required)
       - destination (string, required)
   - Example call:
     {"args": {"date": "05/05/2025", "traveling_from": "Delhi", "destination": "Mumbai"}}

3. Fetch my credit card details from my digital locker before
   - Input parameter: JSON object with key "args"
   - "args" contains:
       - name (string, required)
   - Example call:
     {"args": {"name": "Aswini"}}     

4. Booking my flights based on the flight availability and to book ticket credit card details are required
   - Input parameter: JSON object with key "args"
   - "args" contains:
       - airline (string, required)
       - timing (string, required)
       - date (string, required)
       - credit_card (string, required)
   - Example call:
     {"args": {"airline": "Air India", "timing": "3pm", "date": "05/20/2025" , "credit_card": "0909-xxxx"}}

Always call tools with parameters exactly as shown above.
Do not add extra nesting or omit required fields.

If the user's name, traveling from, or destination are missing or empty, respond by asking:
"Please provide your name and destination details required to proceed with booking."
Do not assume or fill default values.
Only proceed to call tools once the name, traveling from, and destination are provided.

IMPORTANT:
- Your entire response must be a single JSON object parsable by a machine.
- Do NOT include any explanations, notes, or text outside the JSON.
- If the user's query is not related to flight booking, respond ONLY with:
  {"error": "Invalid query: only flight booking requests are supported."}
- Do NOT call any tools or generate any text if the query is invalid.
- If any step fails or information is missing, return a JSON object with an "error" key describing the issue.
"""

system_prompt = """
You are a flight booking assistant with access to these tools:

1. Get my calendar availability
2. Get flight itinerary availability from airlines
3. Fetch my credit card details from digital locker
4. After fetching all the requireds details finally book the ticket

Rules:
- Call exactly ONE tool per response.
- Each tool call must have a unique "id" (e.g., "step1", "step2").
- Wait for the tool's response before making the next call.
- Respond ONLY with a valid JSON tool call wrapped in <tool-use> tags or a final JSON result.
- Do NOT include any free text outside JSON or tool calls.
- If required info is missing, respond with a JSON object requesting it.
- If the query is unrelated to flight booking, respond with:
  {"error": "Invalid query: only flight booking requests are supported."}
"""

mcp_server = MCPServerHTTP(url=BOOKING_MCP_SERVER_URL)

agent = Agent(
    model="groq:llama3-8b-8192",
    mcp_servers=[mcp_server],
    system_prompt=system_prompt,
    # Optional: reduce randomness
    temperature=0.3,
    
)

@app.post("/bookMyFlight1")
async def bookMyFlight1(req: PromptRequest):
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.prompt}
    ]

    async with agent.run_mcp_servers():
        while True:
            response = await agent.run(conversation)
            # Check if response contains a single tool call
            tool_call = extract_single_tool_call(response.data)
            if tool_call:
                # Call MCP server with tool_call parameters
                tool_result = await call_mcp_tool(tool_call)
                # Append agent's tool call and tool's response to conversation
                conversation.append({"role": "assistant", "content": response.data})
                conversation.append({"role": "tool", "content": json.dumps(tool_result)})
            else:
                # No tool calls, final JSON result expected
                try:
                    result = json.loads(response.data)
                    return result
                except Exception:
                    return {"error": "Failed to parse final response as JSON", "raw_response": response.data}
                



def extract_single_tool_call(response_text: str) -> Optional[Dict]:
    """
    Extract a single tool call JSON object from the LLM response wrapped in <tool-use> tags.
    Returns the tool call dict if exactly one tool call is found, else None.
    """
    match = re.search(r"<tool-use>(.*?)</tool-use>", response_text, re.DOTALL)
    if not match:
        return None

    json_str = match.group(1).strip()
    try:
        tool_use_obj = json.loads(json_str)
        tool_calls = tool_use_obj.get("tool_calls", [])
        if len(tool_calls) == 1:
            return tool_calls[0]
        else:
            return None
    except json.JSONDecodeError:
        return None

async def call_mcp_tool(tool_call: Dict) -> Dict:
    """
    Calls the MCP server tool with the given tool_call dictionary.
    Returns the tool output as a dict.
    """
    tool_name = tool_call["function"]["name"]
    args = tool_call["parameters"]["args"]

    try:
        result = await mcp_server.run_tool(tool_name, args)
        return result
    except Exception as e:
        return {"error": f"Failed to call tool '{tool_name}': {str(e)}"}

async def call_groq_model(agent: Agent, prompt_text: str, timeout: float = 60.0):
    """
    Calls the Groq LLM model with a timeout and handles cancellation gracefully.
    """
    try:
        response = await asyncio.wait_for(agent.run(prompt_text), timeout=timeout)
        return response
    except asyncio.TimeoutError:
        return {"error": "Groq API request timed out"}
    except asyncio.CancelledError:
        return {"error": "Groq API request was cancelled"}
    except Exception as e:
        return {"error": f"Groq API request failed: {str(e)}"}

@app.post("/bookMyFlight")
async def bookMyFlight(req: PromptRequest):
    conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.prompt}
    ]

    try:
        async with agent.run_mcp_servers():
            while True:
                # Convert conversation to a single prompt string
                prompt_text = "\n".join(f"{msg['role'].capitalize()}: {msg['content']}" for msg in conversation)
                response = await call_groq_model(agent, prompt_text)

                # If response is an error dict, return it immediately
                if isinstance(response, dict) and "error" in response:
                    return response

                response_text = response.data

                tool_call = extract_single_tool_call(response_text)
                if tool_call:
                    # Call MCP server tool
                    tool_result = await call_mcp_tool(tool_call)

                    # Append assistant's tool call and tool's response to conversation
                    conversation.append({"role": "assistant", "content": response_text})
                    conversation.append({"role": "tool", "content": json.dumps(tool_result)})

                else:
                    # No tool call found - treat as final JSON result
                    try:
                        result = json.loads(response_text)
                        return result
                    except Exception:
                        return {
                            "error": "Failed to parse final agent response as JSON",
                            "raw_response": response_text,
                        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")