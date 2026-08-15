.PHONY: up down test test-api test-web regression
up:
	docker compose up --build
down:
	docker compose down
test: test-api test-web
test-api:
	python -m pytest
test-web:
	npm --prefix apps/web test
regression:
	curl -fsS -X POST http://localhost:$${API_PORT:-8000}/api/v1/regression-runs \
		-H 'Content-Type: application/json' -d '{"seed":194028,"days":30}'
