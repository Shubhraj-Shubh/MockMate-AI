# Production Multi-Language Container for MockMate AI
FROM python:3.11-slim

# Avoid prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install C++ (g++), Java (openjdk-17-jdk-headless), Node.js, curl, and build tools for the code sandbox
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    default-jdk-headless \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . .

# Expose default port
EXPOSE 8000

# Start FastAPI server using uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
