.PHONY: test lint format typecheck ci install clean build-check release worktree-new worktree-remove worktree-list worktree-cleanup

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

typecheck:
	rm -rf .mypy_cache
	mypy src/

ci: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

build-check:
	rm -rf dist/
	python -m build
	twine check dist/*

# --- Worktree helpers for agent teams ---
worktree-new:
	@test -n "$(NAME)" || (echo "Usage: make worktree-new NAME=agent-name" && exit 1)
	git worktree add ../aeo-cli-$(NAME) -b $(NAME)/work main
	cd ../aeo-cli-$(NAME) && python3 -m pip install -e ".[dev]"
	@echo "Worktree ready at ../aeo-cli-$(NAME)"

worktree-remove:
	@test -n "$(NAME)" || (echo "Usage: make worktree-remove NAME=agent-name" && exit 1)
	git worktree remove ../aeo-cli-$(NAME) --force
	git worktree prune
	@echo "Worktree ../aeo-cli-$(NAME) removed"

worktree-list:
	git worktree list

worktree-cleanup:
	git worktree prune
	@echo "Stale worktree entries pruned"

release:
	@test -n "$(VERSION)" || (echo "Usage: make release VERSION=x.y.z" && exit 1)
	sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	git add pyproject.toml
	git commit -m "Release v$(VERSION)"
	git tag v$(VERSION)
	git push origin main --tags
