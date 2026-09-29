ADMIN_TOKEN ?= change-me-local-admin

up:
	docker compose up --build

down:
	docker compose down

seed:
	curl -X POST http://localhost:8000/api/dev/seed -H "Authorization: Bearer $(ADMIN_TOKEN)"

embed:
	curl -X POST http://localhost:8000/api/ml/embed-events -H "Authorization: Bearer $(ADMIN_TOKEN)"
