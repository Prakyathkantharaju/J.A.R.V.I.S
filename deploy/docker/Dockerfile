# JARVIS Docker Image
# Base image for sync and CLI services

FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY config/ ./config/

# Install dependencies
RUN uv sync

# Create data directories
RUN mkdir -p /var/lib/jarvis /var/log/jarvis

# Default command
CMD ["uv", "run", "jarvis", "--help"]
