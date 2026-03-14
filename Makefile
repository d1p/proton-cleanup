.PHONY: install dev test lint clean flatpak

# Default Python executable (override with: make install PYTHON=python3.12)
PYTHON ?= python3

install:  ## Install the package in the active environment
	$(PYTHON) -m pip install .

dev:  ## Install in editable mode with dev dependencies
	$(PYTHON) -m pip install -e ".[dev]"

test:  ## Run the test suite
	$(PYTHON) -m pytest -q

lint:  ## Run ruff linter (install with: pip install ruff)
	$(PYTHON) -m ruff check src tests

format:  ## Auto-format with ruff
	$(PYTHON) -m ruff format src tests

flatpak:  ## Build a distributable Flatpak bundle
	./scripts/build-flatpak.sh

clean:  ## Remove build artifacts
	rm -rf build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
