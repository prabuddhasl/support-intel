.PHONY: \
	migrate stamp reset start \
	install-python-dev install-frontend install-customer-portal \
	lint-python format-python typecheck-python lint-frontend lint-customer-portal lint \
	test \
	up down ps logs logs-enricher enricher status

DATABASE_URL ?= postgresql+psycopg://app:app@localhost:5432/supportintel

migrate:
	DATABASE_URL=$(DATABASE_URL) alembic upgrade head

stamp:
	DATABASE_URL=$(DATABASE_URL) alembic stamp head

install-python-dev:
	pip install -r requirements-dev.txt

install-frontend:
	cd frontend && npm install

install-customer-portal:
	cd customer-portal && npm install

lint-python:
	ruff check .

format-python:
	black .

typecheck-python:
	mypy services

lint-frontend:
	cd frontend && npm run lint

lint-customer-portal:
	cd customer-portal && npm run lint

lint: lint-python typecheck-python lint-frontend lint-customer-portal

test:
	pytest

up:
	docker compose up -d --build

down:
	docker compose down

reset:
	docker compose down -v

start:
	docker compose down -v
	docker compose up -d --build
	make migrate
	docker compose up -d enricher

ps:
	docker compose ps

logs:
	docker compose logs -f

logs-enricher:
	docker compose logs -f enricher

enricher:
	docker compose up -d enricher

status:
	docker compose ps
