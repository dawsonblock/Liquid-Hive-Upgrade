##
# Multi‑stage Dockerfile for the Fusion HiveMind Capsule service.
#
# The first stage installs all Python dependencies into an isolated prefix.  The
# second stage copies the installed dependencies and the application source
# into a minimal runtime image.  A non‑root user is used to drop privileges.
##

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies and copy requirement specifiers
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

# Disable writing .pyc files and flush Python output immediately
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Create a non‑privileged user to run the service
RUN useradd -ms /bin/bash appuser

WORKDIR /app

# Copy installed dependencies from builder image
COPY --from=builder /install /usr/local

# Copy application source
COPY . /app

# Ensure the non‑root user owns the application directory
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# When the container starts run the unified runtime.  The host/port can be
# overridden at runtime via environment variables.  We reference the fully
# qualified module path so that Python can locate the package within
# ``unified_runtime``.
CMD ["python", "-m", "unified_runtime.server"]