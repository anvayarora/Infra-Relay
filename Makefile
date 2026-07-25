.PHONY: up down logs build test backend-test frontend-test
up:
	docker compose up -d --build
build:
	docker compose build
down:
	docker compose down
logs:
	docker compose logs -f --tail=200
backend-test:
	cd backend && pytest -q
frontend-test:
	cd frontend && npm run lint && npm run build
test: backend-test frontend-test
