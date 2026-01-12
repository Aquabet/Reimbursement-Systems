# API Gateway

Routes requests to appropriate microservices and handles cross-cutting concerns.

## Services Routes

### `POST /v1/reports` → Report Service
### `GET /v1/reports/<id>` → Report Service
### `PUT /v1/reports/<id>` → Report Service
### `DELETE /v1/reports/<id>` → Report Service

### `POST /v1/reports/<id>/submit` → Report Service
### `POST /v1/reports/<id>/approve` → Review Service
### `POST /v1/reports/<id>/reject` → Review Service

### `GET /v1/review/inbox` → Review Service
### `GET /v1/review/<id>` → Review Service

### `POST /v1/receipts` → Receipt Service
### `GET /v1/receipts/<id>` → Receipt Service
### `PUT /v1/receipts/<id>` → Receipt Service
### `GET /v1/receipts/report/<report_id>` → Receipt Service

## Features

- Authentication & authorization
- Rate limiting
- Request/response logging
- Error handling
- Service discovery
- Health check aggregation
