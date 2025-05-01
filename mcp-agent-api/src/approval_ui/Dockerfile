# syntax=docker/dockerfile:experimental
FROM python:3.12-slim

WORKDIR /app

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . ./

# Expose the port
EXPOSE 8007

# Command to run the application
CMD ["uvicorn", "approval_ui:app", "--host", "0.0.0.0", "--port", "8007"]
