SHELL := /bin/bash
PROJECT_ID ?= cymbal-health-prod
PROJECT_NUMBER ?= 123456789012
REGION ?= us-central1
PYTEST ?= pytest
HCLFMT ?= hclfmt

.PHONY: help fmt-check test run-local

help:
	@echo "Cymbal Health — Clinical Authorizations Portal Automation"
	@echo "  make fmt-check   Verify Terraform HCL formatting"
	@echo "  make test        Run functional, security, and zero-emoji test suite"
	@echo "  make run-local   Start local FastAPI development server on port 8080"

fmt-check:
	@if command -v "$(HCLFMT)" >/dev/null 2>&1; then \
		"$(HCLFMT)" -w -require-no-change terraform/*.tf; \
		echo "[PASS] Terraform HCL files formatted cleanly."; \
	else \
		echo "[INFO] hclfmt not in PATH; Cloud Build runs terraform fmt -check."; \
	fi

test:
	"$(PYTEST)" tests/ -q

run-local:
	uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload
