##
# Multi-stage Production-Ready Dockerfile for Liquid-Hive-Upgrade
#
# This builds a secure, hardened container with:
# - Multi-stage builds for minimal attack surface
# - Non-root user execution
# - Security scanning integration
# - Health checks and observability
##

# ============================================================================
# Build stage 1: Python dependencies
# ============================================================================
FROM python:3.11-slim as python-builder
LABEL stage=python-builder

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Create a virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Build stage 2: Frontend assets
# ============================================================================
FROM node:20-alpine as frontend-builder
LABEL stage=frontend-builder

# Set up Node.js environment for security
RUN addgroup -g 1001 -S nodejs \
    && adduser -S nextjs -u 1001

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --production=false

# Copy source code and build
COPY frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/public ./public
COPY frontend/src ./src

# Build the application
RUN yarn build \
    && yarn cache clean

# ============================================================================
# Build stage 3: Security scanner (optional)
# ============================================================================
FROM aquasec/trivy:latest as security-scanner
COPY --from=python-builder /app /scan-target
RUN trivy fs --exit-code 0 --format table /scan-target

# ============================================================================
# Runtime stage: Production image
# ============================================================================
FROM python:3.11-slim as runtime
LABEL maintainer="Liquid-Hive Team"
LABEL version="2.0.0"
LABEL description="Liquid-Hive-Upgrade: Oracle Provider Router with Planner & Arena"

# Install runtime system dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    dumb-init \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application user and group with specific UID/GID
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser

# Set up Python environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy virtual environment from builder
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory and copy application code
WORKDIR /app

# Copy application files with proper ownership
COPY --chown=appuser:appgroup . /app
COPY --chown=appuser:appgroup src/ /app/src/

# Copy built frontend assets
COPY --from=frontend-builder --chown=appuser:appgroup /app/frontend/dist /app/src/frontend/dist

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data /app/tmp \
    && chown -R appuser:appgroup /app \
    && chmod -R 755 /app \
    && chmod -R 750 /app/logs /app/data /app/tmp

# Add health check script
COPY --chown=appuser:appgroup health-check.sh /usr/local/bin/health-check.sh
RUN chmod +x /usr/local/bin/health-check.sh

# Switch to non-root user
USER appuser:appgroup

# Set up Python path
ENV PYTHONPATH=/app/src:/app

# Expose port
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python - <<'PY' || exit 1
import urllib.request
import sys
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/healthz', timeout=3) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY


# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Add labels for better observability
LABEL org.opencontainers.image.title="Liquid-Hive-Upgrade"
LABEL org.opencontainers.image.description="Oracle Provider Router with Planner & Arena services"
LABEL org.opencontainers.image.vendor="Liquid-Hive"
LABEL org.opencontainers.image.source="https://github.com/liquid-hive/upgrade"
LABEL org.opencontainers.image.documentation="https://docs.liquid-hive.dev"

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Default command
        main
CMD ["python", "-m", "unified_runtime.__main__"]
