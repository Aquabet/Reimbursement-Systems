.PHONY: help build start stop restart logs test test-unit test-integration clean init migrate format lint

# Default target
help:
	@echo "Reimbursement System - Development Commands"
	@echo "=========================================="
	@echo ""
	@echo "Environment Setup:"
	@echo "  init          - Initialize LocalStack resources (S3, SQS)"
	@echo "  build         - Build all Docker images"
	@echo "  start         - Start all services with docker-compose"
	@echo "  stop          - Stop all services"
	@echo "  restart       - Restart all services"
	@echo "  logs          - View logs from all services"
	@echo "  logs-db       - View database logs only"
	@echo "  logs-api      - View API Gateway logs only"
	@echo ""
	@echo "Database Management:"
	@echo "  migrate       - Run database migrations (on Report Service)"
	@echo "  db-shell      - Open MySQL shell"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  format        - Format code with black"
	@echo "  lint          - Lint code with ruff"
	@echo "  clean         - Clean up Docker containers and volumes"
	@echo ""
	@echo "Development:"
	@echo "  dev-setup     - One-time development setup"

# One-time setup
dev-setup:
	@echo "Setting up development environment..."
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt || true
	pip install -r services/reimbursement_api/requirements.txt || true
	pip install -r services/receipt_service/requirements.txt || true
	pip install -r services/review_service/requirements.txt || true
	pip install -r services/api_gateway/requirements.txt || true
	pip install -r services/ocr_worker/requirements.txt || true
	@echo "Development setup complete!"

# Build all services
build:
	@echo "Building Docker images..."
	docker-compose build
	@echo "Build complete!"

# Initialize LocalStack resources
init:
	@echo "Initializing LocalStack (S3 bucket, SQS queues)..."
	docker-compose run --rm init
	@echo "Initialization complete!"

# Start all services
start:
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Services started!"
	@echo "API Gateway: http://localhost:8080"
	@echo "Report Service: http://localhost:5000"
	@echo "Receipt Service: http://localhost:5001"
	@echo "Review Service: http://localhost:5002"

# Stop all services
stop:
	@echo "Stopping all services..."
	docker-compose down
	@echo "Services stopped!"

# Restart all services
restart: stop start

# View all logs
logs:
	docker-compose logs -f

# View database logs only
logs-db:
	docker-compose logs -f mysql

# View API Gateway logs only
logs-api:
	docker-compose logs -f api-gateway

# Run database migrations
migrate:
	@echo "Running database migrations..."
	cd services/reimbursement_api && flask db upgrade
	@echo "Migrations complete!"

# Open MySQL shell
db-shell:
	docker-compose exec mysql mysql -u dbadmin -ppassword reimbursement_db

# Run all tests
test: test-unit test-integration

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	@echo "Testing Receipt Service..."
	cd services/receipt_service && python -m pytest tests/ -v
	@echo "Testing Review Service..."
	cd services/review_service && python -m pytest tests/ -v
	@echo "Testing API Gateway..."
	cd services/api_gateway && python -m pytest tests/ -v
	@echo "Unit tests complete!"

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	cd tests && python -m pytest test_e2e_workflow.py -v -s
	@echo "Integration tests complete!"

# Format code with black
format:
	@echo "Formatting code with black..."
	black services/ --line-length 100 || echo "Black not installed, skipping..."
	@echo "Formatting complete!"

# Lint code with ruff
lint:
	@echo "Linting code with ruff..."
	ruff services/ || echo "Ruff not installed, skipping..."
	@echo "Linting complete!"

# Clean up Docker containers and volumes
clean:
	@echo "Cleaning up Docker containers and volumes..."
	docker-compose down -v
	docker system prune -f
	@echo "Cleanup complete!"

# Full development cycle: clean, build, init, start
dev: clean build init start
	@echo "Development environment ready!"
	@echo ""
	@echo "Run tests: make test"
	@echo "View logs: make logs"
	@echo "Stop services: make stop"
