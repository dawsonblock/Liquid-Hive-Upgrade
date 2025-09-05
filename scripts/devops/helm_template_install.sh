#!/usr/bin/env bash
set -euo pipefail

IMAGE_REPO=${1:-ghcr.io/your-org/liquid-hive}
IMAGE_TAG=${2:-latest}
NAMESPACE=${3:-default}
VALUES_FILE=${4:-helm/liquid-hive/values-dev.yaml}
CHART_DIR=$(cd "$(dirname "$0")/../liquid_hive_src/LIQUID-HIVE-main/helm/liquid-hive" && pwd)

export KUBECONFIG=${KUBECONFIG:-$HOME/.kube/config}

echo "Helm template…"
helm template lh "$CHART_DIR" -f "$CHART_DIR/$(basename "$VALUES_FILE")" \
  --set image.repository="$IMAGE_REPO" --set image.tag="$IMAGE_TAG" >/dev/null

echo "Helm upgrade/install…"
helm upgrade --install lh "$CHART_DIR" -n "$NAMESPACE" --create-namespace \
  -f "$CHART_DIR/$(basename "$VALUES_FILE")" \
  --set image.repository="$IMAGE_REPO" --set image.tag="$IMAGE_TAG"

echo "Rollout status…"
kubectl -n "$NAMESPACE" rollout status deploy/liquid-hive --timeout=180s
