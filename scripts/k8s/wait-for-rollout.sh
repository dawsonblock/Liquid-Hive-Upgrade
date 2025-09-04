#!/usr/bin/env bash
set -euo pipefail
KIND="${1:-deployment}"
NAME="${2:?name required}"
NAMESPACE="${3:-default}"
TIMEOUT="${4:-300}"
kubectl -n "${NAMESPACE}" rollout status "${KIND}/${NAME}" --timeout="${TIMEOUT}s"
