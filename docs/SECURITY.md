# Security

- Containers: non-root, readOnlyRootFilesystem, drop ALL caps, no privilege escalation.
- Supply chain: SBOM (syft), image scan (trivy), signing + provenance (cosign).
- K8s: NetworkPolicies default-deny, PDB, HPA, ResourceQuota, LimitRange, Pod Security restricted.
- Secrets from ESO only; rotate keys periodically.
- Enable rate limiting and JWT/RBAC in app (wire to Kubernetes SA as needed).
