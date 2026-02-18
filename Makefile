.PHONY: test lint format typecheck ci install clean build-check release

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	mypy src/

ci: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

build-check:
	rm -rf dist/
	python -m build
	twine check dist/*

release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=x.y.z" && exit 1)
	sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	git add pyproject.toml
	git commit -m "Release v$(VERSION)"
	git tag v$(VERSION)
	git push origin main --tags
