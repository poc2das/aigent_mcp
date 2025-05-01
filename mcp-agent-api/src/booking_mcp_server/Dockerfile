# Use official Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements file (adjust if you have one)
COPY requirements.txt .

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy your Math MCP server source code
COPY . .

# Expose ports:
EXPOSE 8003

# Set environment variables if needed
ENV PYTHONUNBUFFERED=1

# Command to run the Math MCP server
# If you run MCP server and FastAPI approval UI in same process, use something like:
CMD ["python", "booking_mcp_server.py"]

# If you separate MCP server and approval UI, you might run them differently or use a process manager
