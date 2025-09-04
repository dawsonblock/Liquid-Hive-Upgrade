# Liquid Hive Upgrade - Makefile

SHELL := /bin/bash
PY := python
PIP := pip
IMAGE ?= liquid-hive:dev
IMAGE_REPO ?= ghcr.io/OWNER/REPO/liquid-hive
IMAGE_TAG ?= latest
RELEASE ?= lh

.PHONY: help
help:
	@echo "Common targets:"
	@echo "  make install            # install Python deps"
	@echo "  make test               # run unit tests"
	@echo "  make test-all           # run full test suite"
	@echo "  make docker-build       # build Docker image"
	@echo "  make docker-run         # run Docker image locally"
	@echo "  make helm-install       # install Helm chart"
	@echo "  make helm-uninstall     # uninstall Helm release"
	@echo "  make precommit-install  # install pre-commit git hooks"
	@echo "  make lint               # run linters"
	@echo "  make format             # format code"
	@echo "  make audit              # inventory + duplicate analysis (dry-run)"
	@echo "  make clean              # remove artifacts"
	@echo "  make distclean          # deep clean (node_modules, caches, reports)"

.PHONY: install
install:
	$(PIP) install -U pip wheel
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
	@echo "Install complete"

.PHONY: test
test:
	pytest -q

.PHONY: test-all
test-all:
	pytest -q -m "not slow" || true
	pytest -q

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

.PHONY: docker-run
docker-run:
	docker run --rm -p 8000:8000 $(IMAGE)

.PHONY: helm-install
helm-install:
	helm upgrade --install $(RELEASE) deploy/helm/liquid-hive \
	  --namespace liquid-hive --create-namespace \
	  --set unifiedRuntime.image.repository=$(IMAGE_REPO) \
	  --set unifiedRuntime.image.tag=$(IMAGE_TAG)

.PHONY: helm-uninstall
helm-uninstall:
	helm uninstall $(RELEASE) || true

.PHONY: precommit-install
precommit-install:
	pre-commit install || true

.PHONY: lint
lint:
	ruff check . || true

.PHONY: format
format:
	ruff format . || true
	black . || true
	isort . || true

.PHONY: audit
audit:
	@mkdir -p reports
	$(PY) tools/audit_repo.py
	$(PY) tools/dedupe_by_hash.py

.PHONY: clean
clean:
	$(PY) tools/clean_repo.py --apply

.PHONY: distclean
distclean:
	$(PY) tools/clean_repo.py --apply --deep
