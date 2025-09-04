# Contributing

- Install pre-commit hooks: `make precommit-install`
- Run fast unit tests: `make test`
- Run full suite: `make test-all`
- Export OpenAPI: `make openapi`
- Build & run Docker: `make docker-build && make docker-run`
- Helm install: `make helm-install IMAGE_REPO=ghcr.io/OWNER/REPO/liquid-hive IMAGE_TAG=latest`

Please avoid committing secrets. Keys must be provided via environment or secret managers.
