# Secrets

- No plaintext secrets in repo.
- Use External Secrets Operator (ESO) with ClusterSecretStore (e.g., AWS Secrets Manager, GCP, Vault, SOPS).
- Helm values externalSecrets.* configure the ESO wiring.
- App should read from Kubernetes Secret 'liquid-hive-secrets'. Example keys:
  - PROVIDER_API_KEYS
  - JWT_SIGNING_KEY
- For local dev use SOPS-encrypted .env.enc files and `sops` to decrypt at runtime.
