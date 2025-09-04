#!/usr/bin/env bash
set -euo pipefail

IMAGE_REPO=${1:-ghcr.io/your-org/liquid-hive}
IMAGE_TAG=${2:-latest}
CONTEXT_DIR=$(cd "$(dirname "$0")/../liquid_hive_src/LIQUID-HIVE-main" && pwd)

echo "Building ${IMAGE_REPO}:${IMAGE_TAG} from ${CONTEXT_DIR}"

docker build -t "${IMAGE_REPO}:${IMAGE_TAG}" -f "${CONTEXT_DIR}/Dockerfile" "${CONTEXT_DIR}"
docker push "${IMAGE_REPO}:${IMAGE_TAG}"

echo "Pushed ${IMAGE_REPO}:${IMAGE_TAG}"
