# AutoSRE developer commands. Run `make` (or `make help`) to list targets.
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down restart build logs ps test test-local lint fmt typecheck \
        chaos chaos-reset dashboards clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Build and start the full stack (detached)
	$(COMPOSE) up --build -d
	@echo ""
	@echo "  API docs    http://localhost:8000/docs"
	@echo "  Prometheus  http://localhost:9090"
	@echo "  Grafana     http://localhost:3000  (admin / admin)"

down: ## Stop and remove the stack (keeps data volumes)
	$(COMPOSE) down

restart: down up ## Restart the stack

build: ## Build all images
	$(COMPOSE) build

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

ps: ## Show services and health status
	$(COMPOSE) ps

test: ## Run the full test suite in a container (no local Python needed)
	$(COMPOSE) -f docker-compose.test.yml run --rm --build tests

test-local: ## Run tests locally (requires Python + pip)
	pip install -r requirements-dev.txt && pytest

lint: ## Ruff lint + format check
	ruff check shared api auth worker tests
	ruff format --check shared api auth worker tests

fmt: ## Auto-format the codebase
	ruff format shared api auth worker tests

typecheck: ## Type-check the shared library
	mypy shared/autosre_shared

chaos: ## Run a demo chaos scenario against the running stack
	./scripts/chaos_demo.sh

chaos-reset: ## Disable all chaos on every service
	@for p in 8000 8001 8002; do \
		curl -fsS -XPOST http://localhost:$$p/chaos/reset >/dev/null && echo "reset :$$p"; \
	done

dashboards: ## Open Grafana in the browser
	@python3 -c "import webbrowser; webbrowser.open('http://localhost:3000')" 2>/dev/null || true
	@echo "Grafana http://localhost:3000  ->  RED | Reliability | Chaos | Incident"

clean: ## Tear down the stack with volumes and remove local artifacts
	-$(COMPOSE) down -v --remove-orphans
	rm -rf htmlcov coverage.xml .coverage .pytest_cache
