.PHONY: docs preview test test-heavy lint typecheck check clean clean-tags release-docs build publish-pypi release version

# Extract version from pyproject.toml
VERSION := $(shell grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')

version:
	@echo "Current version: $(VERSION)"

# Dockit documentation site (docs/, pnpm)
docs:
	cd docs && pnpm install --frozen-lockfile && pnpm build

preview:
	cd docs && pnpm dev

# Fast checks: what PR CI runs
lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest -m "not mujoco and not usd and not viewer"

check: lint typecheck test

# Heavy checks (MuJoCo, USD, vuer): local, or the manual "heavy" workflow
test-heavy:
	./scripts/local-checks.sh

clean:
	rm -rf docs/dist build dist *.egg-info

# Documentation release (version tag)
clean-tags:
	@if git rev-parse v$(VERSION) >/dev/null 2>&1; then \
		echo "Removing existing tag v$(VERSION)..."; \
		git tag -d v$(VERSION); \
		git push origin --delete v$(VERSION) 2>/dev/null || true; \
	else \
		echo "Tag v$(VERSION) does not exist, skipping cleanup"; \
	fi

release-docs: clean-tags
	@echo "Releasing documentation version: $(VERSION)"
	@if [ -z "$(MSG)" ]; then \
		git tag v$(VERSION); \
	else \
		git tag v$(VERSION) -m '$(MSG)'; \
	fi
	git tag -f latest
	git push origin v$(VERSION) latest --force
	@echo "Documentation tags pushed successfully"

# Package release (PyPI)
build: clean
	uv build

publish-pypi: build
	uv publish --token $$UV_PYPI_TOKEN

# Full release (both docs and package)
release: release-docs publish-pypi
