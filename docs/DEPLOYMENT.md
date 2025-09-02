# Deployment Guide (Helm + GitHub Actions)

## Overview
This repo ships a Helm chart and CI/CD workflows to build the image, lint the chart, and deploy per environment. Secrets can be synced via external-secrets.

## Prereqs
- Kubernetes cluster with Ingress controller (e.g., nginx) and optionally Prometheus Operator.
- External Secrets Operator (optional, recommended for prod).
- OIDC-enabled CI runner permissions to your cloud.

### AWS EKS (IRSA + OIDC)
- Create an IAM role for service account (IRSA) used by the app when pulling secrets.
- Trust policy (replace OIDC provider ARN and namespace/SA):
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/<EKS_OIDC_PROVIDER>" },
			"Action": "sts:AssumeRoleWithWebIdentity",
			"Condition": {
				"StringEquals": {
					"<EKS_OIDC_PROVIDER>:sub": "system:serviceaccount:liquid-hive-prod:liquid-hive"
				}
			}
		}
	]
}
```
- Inline policy example for Secrets Manager read:
```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "SecretsRead",
			"Effect": "Allow",
			"Action": [
				"secretsmanager:GetSecretValue",
				"secretsmanager:DescribeSecret"
			],
			"Resource": "arn:aws:secretsmanager:<REGION>:<ACCOUNT_ID>:secret:liquid-hive/*"
		}
	]
}
```

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

## Local runs (Docker Compose)
- CPU only:
	- `docker-compose up --build`
- With local NVIDIA GPU for vLLM:
	- `docker-compose --profile gpu up --build`
	- Requires NVIDIA Container Toolkit and a GPU.

## AWS GPU model server
- Ensure a GPU node group exists (p4d, g5, etc.).
- Apply the provided vLLM manifest:
	- `kubectl apply -f k8s/vllm-gpu.yaml`
- Point the app to it via env/secret:
	- `VLLM_ENDPOINT=http://vllm:8000`
- Deploy the app via Helm with `values-aws-prod.yaml`.
