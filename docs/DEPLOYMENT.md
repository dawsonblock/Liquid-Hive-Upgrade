# Liquid-Hive Deployment Guide

## Overview

Liquid-Hive is a comprehensive AI platform with multiple deployment options ranging from local development to production Kubernetes clusters. This guide covers all deployment scenarios including Docker, Docker Compose, and Kubernetes with Helm.

## Quick Start

### Automated Deployment
```bash
# Use the interactive deployment script
./deploy.sh

# Or deploy with Docker Compose directly
docker-compose up -d
```

### Manual Deployment
```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your API keys

# 2. Deploy
docker-compose up -d

# 3. Access services
# - API: http://localhost:8000
# - Frontend: http://localhost:8000
# - Grafana: http://localhost:3000
```

## Prerequisites

### System Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)
- 8GB+ RAM recommended
- GPU recommended for AI workloads

### For Kubernetes Deployment
- kubectl configured for your cluster
- Helm 3.0+
- Kubernetes 1.19+

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

## Deployment Options

### Option 1: Automated Deployment Script

The `deploy.sh` script provides an interactive menu for all deployment scenarios:

```bash
./deploy.sh
```

Available options:
1. **Setup Environment** - Configure directories and environment files
2. **Build Docker Image** - Build the Liquid-Hive Docker image
3. **Deploy with Docker Compose** - Local deployment with all services
4. **Deploy to Kubernetes** - Production deployment with Helm
5. **Run Tests** - Execute backend and frontend test suites
6. **Show Status** - Check deployment status
7. **Cleanup** - Remove all deployed resources

### Option 2: Docker Compose (Recommended for Development)

#### Basic Deployment
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### GPU-Enabled Deployment
```bash
# With GPU support for vLLM
docker-compose --profile gpu up -d
```

#### Development with Live Reload
```bash
# Backend development
docker-compose up -d redis neo4j qdrant
# Then run backend locally for hot reload

# Frontend development
cd frontend
npm run dev
```

### Option 3: Docker Standalone

#### Build and Run
```bash
# Build the image
docker build -t liquid-hive:latest .

# Run with environment file
docker run -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  liquid-hive:latest
```

### Option 4: Local Development

#### Manual Setup
```bash
# Backend
pip install -r requirements.txt
python -m unified_runtime

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

#### With External Services
```bash
# Start only infrastructure services
docker-compose up -d redis neo4j qdrant prometheus grafana

# Run app locally
pip install -r requirements.txt
python -m unified_runtime
```
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

## Local Development

### Docker Compose (Recommended)
- **CPU only**: `docker-compose up --build`
- **With GPU**: `docker-compose --profile gpu up --build`
- **Requires**: NVIDIA Container Toolkit and GPU for vLLM

### Manual Development
```bash
# Start infrastructure
docker-compose up -d redis neo4j qdrant

# Backend development
pip install -r requirements.txt
python -m unified_runtime

# Frontend development (separate terminal)
cd frontend
npm install
npm run dev
```

### Testing
```bash
# Run all tests
./deploy.sh  # Select option 5

# Manual testing
pytest tests/
cd frontend && npm test
```

## AWS GPU model server
- Ensure a GPU node group exists (p4d, g5, etc.).
- Apply the provided vLLM manifest:
	- `kubectl apply -f k8s/vllm-gpu.yaml`
- Point the app to it via env/secret:
	- `VLLM_ENDPOINT=http://vllm:8000`
- Deploy the app via Helm with `values-aws-prod.yaml`.
