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
	@echo "  make test               # run fast unit tests (planner + arena)"
	@echo "  make test-all           # run full test suite"
	@echo "  make openapi            # export OpenAPI to docs/openapi.json"
	@echo "  make docker-build       # build Docker image"
	@echo "  make docker-run         # run Docker image locally"
	@echo "  make helm-install       # install Helm chart"
	@echo "  make helm-uninstall     # uninstall Helm release"
	@echo "  make precommit-install  # install pre-commit git hooks"
	@echo "  make lint               # run ruff checks"
	@echo "  make format             # run formatters (ruff, black, isort if available)"

.PHONY: install
install:
	$(PIP) install -U pip wheel
	@if [ -f requirements.txt ]; then $(PIP) install -r requirements.txt; fi
	@echo "Install complete"

.PHONY: test
test:
	ENABLE_ARENA=true pytest -q tests/test_planner.py tests/test_arena.py

.PHONY: test-all
test-all:
	pytest -q

.PHONY: openapi
openapi:
	$(PY) scripts/export_openapi.py

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

.PHONY: docker-run
docker-run:
	docker run --rm -p 8000:8000 $(IMAGE)

.PHONY: helm-install
helm-install:
	helm upgrade --install $(RELEASE) ./helm \
	  --set image.repository=$(IMAGE_REPO) \
	  --set image.tag=$(IMAGE_TAG)

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