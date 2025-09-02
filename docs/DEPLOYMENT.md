# Deployment Guide (Helm + GitHub Actions)

## Overview
This repo ships a Helm chart and CI/CD workflows to build the image, lint the chart, and deploy per environment. Secrets can be synced via external-secrets.

## Prereqs
- Kubernetes cluster with Ingress controller (e.g., nginx) and optionally Prometheus Operator.
- External Secrets Operator (optional, recommended for prod).
- OIDC-enabled CI runner permissions to your cloud.

## CI/CD
- CI workflow: builds frontend, runs tests, builds backend, lints Helm, scans with Trivy, emits SBOM.
- Dev CD: deploys to `liquid-hive-dev` namespace on main.
- Prod CD: deploys on tag (vX.Y.Z) or manual dispatch to `liquid-hive-prod`.

## Images
Set your registry in workflows. The chart accepts `image.repository` and `image.tag`.

## Helm values
- Base: `helm/liquid-hive/values.yaml`.
- Dev: `helm/liquid-hive/values-dev.yaml`.
- Prod: `helm/liquid-hive/values-aws-prod.yaml`.

Feature toggles:
- `autoscaling.enabled`: creates HPA (v2)
- `pdb.enabled`: creates PodDisruptionBudget
- `networkPolicy.enabled`: creates a deny-by-default NP unless rules provided
- `serviceMonitor.enabled`: creates ServiceMonitor for /metrics
- `externalSecrets.enabled`: creates ExternalSecret; configure `secretStore`+`data`

## Secrets
- For AWS SM: configure ClusterSecretStore (see `secretstore-example.yaml`) and map keys in `values.externalSecrets.data`.
- For Vault: set `secrets.provider=vault` and configure `.Values.secrets.vault.*`.

## Health and probes
- Liveness/Readiness: `/api/healthz`
- Metrics: `/metrics` (ensure enabled in app)

## Quick dry run
```
helm lint helm/liquid-hive
helm template demo helm/liquid-hive -f helm/liquid-hive/values.yaml | less
```
