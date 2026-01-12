# Phase 1 — Modular Monolith API Foundation

## Goals

- Establish a working backend API
- Apply clean architecture boundaries

## Tasks

- Implement base Flask application:
- `create_app()` factory
- Blueprint-based routing
- Enforce layered architecture:
- API (controllers)
- Application (use cases)
- Domain (models, policies)
- Infrastructure (DB, messaging)
- Configure MySQL (RDS-compatible) schema
- Add Alembic migrations

## Deliverables

- Running API service
- Initial database schema

## Acceptance Criteria

- `POST /v1/reports` creates a report
- `GET /v1/reports/{id}` returns persisted data
