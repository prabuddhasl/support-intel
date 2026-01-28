.PHONY: \
	migrate stamp reset start wait-db create-topics health doctor dev clean seed \
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

doctor:
	python scripts/doctor.py

dev:
	make start
	docker compose logs -f api enricher

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.pyc" -delete

seed:
	bash scripts/seed_kb.sh
	bash scripts/seed_tickets.sh

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
	make wait-db
	make create-topics
	make migrate
	docker compose up -d enricher

wait-db:
	@echo "Waiting for Postgres to be ready..."
	@until docker exec support-intel-postgres-1 pg_isready -U app -d supportintel >/dev/null 2>&1; do \
		sleep 1; \
	done

create-topics:
	@echo "Ensuring Kafka topics exist..."
	@docker exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server kafka:9092 \
		--create --if-not-exists --topic support.tickets.v1 --partitions 1 --replication-factor 1 >/dev/null
	@docker exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server kafka:9092 \
		--create --if-not-exists --topic support.enriched.v1 --partitions 1 --replication-factor 1 >/dev/null
	@docker exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server kafka:9092 \
		--create --if-not-exists --topic support.dlq.v1 --partitions 1 --replication-factor 1 >/dev/null

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

health:
	@echo "== Services ==" && docker compose ps
	@echo "== API /health ==" && (curl -fsS http://localhost:8000/health || echo "API unhealthy or not reachable")
	@echo "== Postgres ==" && (docker exec support-intel-postgres-1 psql -U app -d supportintel -c "SELECT 1" >/dev/null && echo "OK" || echo "DB unhealthy or not reachable")
	@echo "== Kafka topics ==" && (docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list || echo "Kafka unhealthy or not reachable")
