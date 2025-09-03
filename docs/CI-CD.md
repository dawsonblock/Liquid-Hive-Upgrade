# CI/CD

- Workflow: .github/workflows/ci-hardening.yml
- Stages: prepare (lint/scan), build_and_sbom (buildx, SBOM, scan), sign_and_attest (cosign keyless), optional kind_smoke.
- Set REGISTRY to ghcr.io/ORG. Override unifiedRuntime.image.* via Helm in deploy steps.
- Provide OIDC permissions for GHCR and cosign keyless.
- Add jobs for unit/integration/e2e once tests exist (Makefile targets or scripts).

Artifacts:
- SBOMs: artifacts/sbom/*.spdx.json
- Images list: artifacts/images.txt

Secrets:
- None required for keyless signing; GH_TOKEN is used for GHCR login.
