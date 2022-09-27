.PHONY: clean test dev venv install coverage

test: install ## run the project's unit tests
	scripts/test.sh

dev: venv install .git/hooks/pre-commit ## set up local dev environment including pre-commit checks

coverage: install ## run code coverage
	scripts/coverage.sh

clean: ## delete the venv and cached files
	scripts/clean.sh

update-pre-commit: venv install scripts/update-pre-commit-rules.sh ## update the pre-commit hook scripts to the latest version
	scripts/update-pre-commit-rules.sh

venv: venv/bin/activate

install: venv/.installed

# note: non-phony requirements can't rely on phony ones

venv/.installed: venv/bin/activate pyproject.toml scripts/install.sh
	scripts/install.sh
	touch venv/.installed

venv/bin/activate: scripts/venv.sh
	scripts/venv.sh

.git/hooks/pre-commit: scripts/install-pre-commit-hook.sh
	scripts/install-pre-commit-hook.sh

help:
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-30s\033[0m %s\n", $$1, $$2}'
