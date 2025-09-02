##
# Multi‑stage Dockerfile for the Fusion HiveMind Capsule service.
#
# This builds the Cerebral GUI with Vite and serves it from FastAPI.
#
##

# 1) Build Python dependencies
FROM python:3.11-slim as pybuilder
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# 2) Build the Cerebral GUI
FROM node:20-alpine as guibuilder
WORKDIR /app/gui
# Use npm to leverage the committed package-lock.json and avoid relying on yarn availability
COPY frontend/package.json ./package.json
COPY frontend/package-lock.json ./package-lock.json
COPY frontend/tsconfig.json ./tsconfig.json
COPY frontend/vite.config.ts ./vite.config.ts
COPY frontend/index.html ./index.html
COPY frontend/src ./src
RUN npm ci && npm run build

# 3) Runtime image
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Include src on PYTHONPATH now that code has moved under /app/src
ENV PYTHONPATH=/app/src:/app
RUN useradd -ms /bin/bash appuser
WORKDIR /app
# Copy python deps
COPY --from=pybuilder /install /usr/local
# Copy repository
COPY . /app
# Copy built GUI from guibuilder stage
COPY --from=guibuilder /app/gui/dist /app/src/capsule_brain/gui/static
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["python", "-m", "unified_runtime.__main__"]