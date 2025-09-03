Secrets Management
Overview
- Production: use External Secrets Operator to sync secrets from a cloud provider (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) into Kubernetes Secrets mounted as env.
- Fallback/Local: use SOPS-encrypted YAML checked into git; decrypt at deploy time with CI OIDC or local age key.

External Secrets (AWS example)
- Install External Secrets Operator in your cluster.
- Configure a ClusterSecretStore referencing AWS via IRSA (OIDC): see `helm/liquid-hive/templates/externalsecret.yaml` and `helm/liquid-hive/values-aws-prod.yaml`.
- Populate secrets in AWS Secrets Manager with keys matching values under `externalSecrets.data`.

CLI flow (AWS):
- aws configure (or OIDC in CI).
- aws secretsmanager create-secret --name liquid-hive/prod/OPENAI_API_KEY --secret-string 'sk-***'
- Repeat for: DEEPSEEK_API_KEY, DEEPSEEK_R1_API_KEY, ANTHROPIC_API_KEY, QWEN_API_KEY, ADMIN_TOKEN, OTEL_EXPORTER_OTLP_ENDPOINT, etc.
- helm upgrade --install liquid-hive helm/liquid-hive -n liquid-hive-prod -f helm/liquid-hive/values.yaml -f helm/liquid-hive/values-aws-prod.yaml

GCP/Azure
- Add a ClusterSecretStore for your provider and map `externalSecrets.data` similarly.

SOPS Fallback
- SOPS config: see `sops.yaml`.
- Generate an age key locally:
  - age-keygen -o ~/.config/sops/age/keys.txt
  - export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
- Encrypt a file:
  - cp helm/secrets/example.enc.yaml helm/secrets/runtime.enc.yaml
  - sops -e -i helm/secrets/runtime.enc.yaml
- Decrypt for local deploy:
  - sops -d helm/secrets/runtime.enc.yaml > /tmp/runtime.yaml
  - kubectl -n liquid-hive-dev apply -f /tmp/runtime.yaml

Notes
- Never commit plaintext secrets.
- CI uses OIDC + keyless cosign; prefer IRSA/workload identity for cloud auth.
- In Helm, envs are sourced via ExternalSecret (envFrom) and values (ConfigMap) for non-secret defaults.

