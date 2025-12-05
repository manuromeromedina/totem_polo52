.PHONY: test-backend test-frontend build-backend build-frontend compose-up compose-down

test-backend:
	cd backend && pytest -m "not integration"

test-frontend:
	cd frontend && npm run test -- --watch=false --code-coverage

build-backend:
	docker build -f backend/Dockerfile -t polo52-backend .

build-frontend:
	docker build -f frontend/Dockerfile -t polo52-frontend .

compose-up:
	docker compose -f docker-compose.dev.yml up --build

compose-down:
	docker compose -f docker-compose.dev.yml down --remove-orphans
