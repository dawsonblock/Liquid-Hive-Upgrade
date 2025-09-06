# Multi-stage build for production-ready API
FROM python:3.11-slim as base

# Install system dependencies and security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with better caching
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install security updates and runtime dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID/GID
RUN groupadd -g 1001 app && \
    useradd -r -u 1001 -g app -d /app -s /bin/bash app

# Copy Python packages from builder
COPY --from=base /root/.local /home/app/.local

# Set up working directory
WORKDIR /app

# Copy source code (from repo root context)
COPY --chown=app:app src/ ./src/
COPY --chown=app:app apps/api/ ./apps/api/

# Set environment variables
ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start application with dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
