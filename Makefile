.PHONY: test lint format typecheck ci install clean build-check release worktree-new worktree-remove worktree-list worktree-cleanup coverage audit help
.DEFAULT_GOAL := help

install: ## Install dev dependencies
	pip install -e ".[dev]"

test: ## Run test suite
	pytest tests/ -v

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Format code with ruff
	ruff format src/ tests/

typecheck: ## Run mypy type checker
	rm -rf .mypy_cache
	mypy src/

ci: ## Run lint + typecheck + tests
ci: lint typecheck test

clean: ## Remove build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

build-check: ## Build and check package
	rm -rf dist/
	python -m build
	twine check dist/*

# --- Worktree helpers for agent teams ---
worktree-new:
	@test -n "$(NAME)" || (echo "Usage: make worktree-new NAME=agent-name" && exit 1)
	git worktree add ../context-cli-$(NAME) -b $(NAME)/work main
	cd ../context-cli-$(NAME) && python3 -m pip install -e ".[dev]"
	@echo "Worktree ready at ../context-cli-$(NAME)"

worktree-remove:
	@test -n "$(NAME)" || (echo "Usage: make worktree-remove NAME=agent-name" && exit 1)
	git worktree remove ../context-cli-$(NAME) --force
	git worktree prune
	@echo "Worktree ../context-cli-$(NAME) removed"

worktree-list:
	git worktree list

worktree-cleanup:
	git worktree prune
	@echo "Stale worktree entries pruned"

release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=x.y.z" && exit 1)
	@echo "Checking README.md was updated..."
	@git diff --name-only HEAD~5 2>/dev/null | grep -q README.md || \
		(echo "WARNING: README.md not updated recently. Review before releasing." && exit 1)
	sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	git add pyproject.toml
	git commit -m "Release v$(VERSION)"
	git tag v$(VERSION)
	git push origin main --tags

coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=context_cli --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

audit: ## Run security audit on dependencies
	pip-audit

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
