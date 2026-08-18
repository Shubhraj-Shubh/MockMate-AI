# Production Multi-Language Container for MockMate AI Backend
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install C++ (g++), Java (openjdk-17-jdk-headless), Node.js, and compiler tools for Sandbox
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    default-jdk-headless \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files into container
COPY backend/ .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
