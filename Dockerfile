# QuantCoder CLI - Production Dockerfile
# Multi-stage build for optimized image size

# =====================================
# Stage 1: Build environment
# =====================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only dependency files first (for caching)
COPY pyproject.toml requirements.txt ./

# Install Python dependencies with secure build tools
RUN pip install --no-cache-dir --upgrade pip>=25.3 setuptools>=78.1.1 wheel>=0.46.2 && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest pytest-asyncio

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# =====================================
# Stage 2: Production runtime
# =====================================
FROM python:3.11-slim as production

LABEL maintainer="SL-MAR <smr.laignel@gmail.com>"
LABEL version="2.0.0"
LABEL description="QuantCoder CLI - AI-powered trading algorithm generator"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY quantcoder/ ./quantcoder/
COPY pyproject.toml README.md LICENSE ./

# Install the package
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash quantcoder
USER quantcoder

# Create directories for data persistence
RUN mkdir -p /home/quantcoder/.quantcoder \
    /home/quantcoder/downloads \
    /home/quantcoder/generated_code \
    /home/quantcoder/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME=/home/quantcoder

# Default config directory
ENV QUANTCODER_HOME=/home/quantcoder/.quantcoder

# Health check - verify CLI is working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD quantcoder --version || exit 1

# Volumes for persistence
VOLUME ["/home/quantcoder/.quantcoder", "/home/quantcoder/downloads", "/home/quantcoder/generated_code"]

# Entry point
ENTRYPOINT ["quantcoder"]
CMD ["--help"]
