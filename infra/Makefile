.PHONY: test dev-backend dev-frontend seal-generator run-final compose-up compose-down

test:
	cd .. && uv run pytest -q

dev-backend:
	cd .. && AUSHADHI_MODE=local uv run uvicorn backend.app:app --reload --port 8000

dev-frontend:
	cd ../frontend && npm run dev

seal-generator:
	cd .. && uv run python -m eval.seal_generator

run-final:
	cd .. && uv run python -m eval.run_final

compose-up:
	docker compose -f docker-compose.yml up --build

compose-down:
	docker compose -f docker-compose.yml down
