FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . ./


# Expose port for FastAPI app
EXPOSE 8004

# Command to run the FastAPI app
#CMD ["uvicorn", "llm_client_sampling", "--host", "0.0.0.0", "--port", "8004"]
CMD ["python", "llm_client_sampling.py"]
