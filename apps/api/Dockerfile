FROM python:3.12-slim AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy pyproject.toml and install dependencies
COPY pyproject.toml .

# Install Python dependencies (cloud-only: no torch/pyannote/ML packages)
RUN pip install --no-cache-dir .[cloud]

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the API server with env file from /secrets
CMD ["/bin/sh", "-c", "if [ -f /secrets/.env.prod ]; then set -a && . /secrets/.env.prod && set +a; fi && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
