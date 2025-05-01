FROM python:3.12-slim

WORKDIR /app

# Install CA certs + openssl
RUN apt-get update && apt-get install -y \
    ca-certificates \
    openssl \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --timeout=100 -r requirements.txt

# Copy app
COPY . ./

EXPOSE 8002

CMD ["uvicorn", "fastapi_agent:app", "--host", "0.0.0.0", "--port", "8002"]
