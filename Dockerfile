# RFSN Sandbox Controller - Docker Environment
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rfsn_controller/ /app/rfsn_controller/
COPY README.md /app/

# Create sandbox directory
RUN mkdir -p /sandbox

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RFSN_SANDBOX_BASE=/sandbox

# Create non-root user for safety
RUN useradd -m -u 1000 rfsn && \
    chown -R rfsn:rfsn /app /sandbox
USER rfsn

# Default command (use ENTRYPOINT to allow args)
ENTRYPOINT ["python", "-m", "rfsn_controller.cli"]
