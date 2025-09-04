# Release

- Tag release: v1.0.0 using conventional commits and changelog generation (e.g., git-cliff).
- CI builds multi-arch images, SBOMs, scans, signs with cosign keyless, and attests provenance.
- Promote Helm chart with immutable version; publish to OCI registry if desired (helm push oci://ghcr.io/ORG/charts).
