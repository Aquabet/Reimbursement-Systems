# Microservices Architecture - Phase 9

This directory contains the microservices extracted from the monolithic reimbursement API.

## Services Overview

### 1. Report Service (`reimbursement_api/`)
- **Port**: 5000
- **Database**: Reports, Report states, Audit logs
- **Security**: JWT-based authentication with secret management via AWS Secrets Manager.
- **Observability**: Emits structured JSON logs.
- **Responsibilities**:
  - Report CRUD operations
  - Report state management (DRAFT → SUBMITTED → REVIEW → APPROVED/REJECTED)
  - Report aggregation and totals
  - Synchronous operations only

### 2. Receipt Service (`receipt_service/`)
- **Port**: 5001
- **Database**: Receipts table, Validation results (logically decoupled)
- **Security**: JWT-based authentication with secret management via AWS Secrets Manager.
- **Observability**: Emits structured JSON logs.
- **Responsibilities**:
  - Receipt CRUD operations
  - Receipt upload and storage
  - Validation result storage and retrieval
  - Integration with OCR and Validation queues
  - Event publishing (receipt.created, receipt.ocr_completed, receipt.validated) to AWS SNS Topic

**API Endpoints**:
- POST `/v1/receipts` - Create receipt
- GET `/v1/receipts/<id>` - Get receipt
- PUT `/v1/receipts/<id>` - Update receipt
- DELETE `/v1/receipts/<id>` - Delete receipt
- GET `/v1/receipts/report/<report_id>` - Get receipts by report
- GET `/v1/receipts/<id>/validation` - Get validation results
- GET `/v1/receipts/report/<report_id>/validation-summary` - Get validation summary

### 3. Review Service (`review_service/`)
- **Port**: 5002
- **Database**: Reports (read-only for inbox), Audit logs, Review comments
- **Security**: JWT-based authentication with secret management via AWS Secrets Manager.
- **Observability**: Emits structured JSON logs.
- **Responsibilities**:
  - Review inbox management
  - Report approval/rejection
  - Review workflow and audit logging
  - Cross-service communication (calls Receipt Service for validation data)
  - Event publishing (report.approved, report.rejected) to AWS SNS Topic

**API Endpoints**:
- GET `/v1/review/inbox` - Get review inbox
- GET `/v1/review/<report_id>` - Get report details for review
- POST `/v1/review/<report_id>/approve` - Approve report
- POST `/v1/review/<report_id>/reject` - Reject report

### 4. API Gateway (`api_gateway/`)
- **Port**: 8080 (external)
- **Responsibilities**:
  - Request routing to appropriate microservices
  - Authentication and authorization (JWT validation)
  - Rate limiting and request logging
  - Service discovery and health checking
  - Cross-cutting concerns management
  - **Security**: JWT validation with secret management via AWS Secrets Manager.
  - **Observability**: Structured JSON logging, request ID tracking, standardized error handling.
  - **Features**: Rate limiting with Flask-Limiter.

**Routes**:
- `/v1/reports/*` → Report Service (5000)
- `/v1/receipts/*` → Receipt Service (5001)
- `/v1/review/*` → Review Service (5002)

### 5. OCR Worker (`ocr_worker/`)
- **Responsibilities**: Asynchronous OCR processing of uploaded receipts.
- **Communicates via**: Consumes messages from the `OCR_QUEUE` (SQS) for new OCR jobs. Publishes `receipt.ocr_completed` events to SNS upon completion.
- **Observability**: Emits structured JSON logs.

### 6. Validation Worker (`ocr_worker/validation_main.py`)
- **Responsibilities**: Asynchronous validation of OCR results using MCP (Multi-Cloud Platform) capabilities.
- **Communicates via**: Consumes messages from the `VALIDATION_QUEUE` (SQS) for new validation jobs. Publishes `receipt.validated` events to SNS upon completion.
- **Observability**: Emits structured JSON logs.

## Communication Patterns

### Synchronous (HTTP)
- API Gateway → Microservices
- Review Service → Receipt Service (for validation data)
- Service mesh pattern with direct service-to-service calls

### Asynchronous (Events)
- Receipt Service publishes events:
  - `receipt.created` - New receipt uploaded
  - `receipt.ocr_completed` - OCR processing finished
  - `receipt.validated` - Validation completed

- Review Service publishes events:
  - `report.approved` - Report approved
  - `report.rejected` - Report rejected

- Workers consume from SQS:
  - OCR queue → OCR Worker
  - Validation queue → Validation Worker

## Message Bus

The system uses an abstract message bus that can be configured for different environments:

### Production: AWS SNS/SQS
- High reliability and durability
- Integration with AWS services
- Fan-out capabilities via SNS topics

### Development: Local Message Bus
- In-memory pub/sub
- No external dependencies
- Simplified debugging

## Database Strategy

**Shared Database Pattern**: All services share the same MySQL database but access different tables:
- Report Service: Reports, AuditLogs
- Receipt Service: Receipts, ValidationResults
- Review Service: ReviewComments (reads from Reports and AuditLogs)

**Trade-offs**:
- ✅ Simpler migration path from monolith
- ✅ Single database to manage
- ✅ Cross-service queries without distributed transactions
- ❌ Schema changes affect multiple services
- ❌ Tight coupling at database level

**Future Evolution**: Consider database-per-service with event sourcing for complete decoupling.

## Deployment

### Terraform Infrastructure

Located in `infrastructure/terraform/`:
- `modules/services/` - ECS services for microservices
- `modules/ecs/` - Common ECS configurations
- `staging/` - Staging environment variables and main.tf

Deployment commands:
```bash
cd infrastructure/terraform/staging
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Local Development

1. **Start all services** (in separate terminals):
```bash
# Report Service
FLASK_ENV=dev python services/reimbursement_api/reimbursement_api/app.py

# Receipt Service
FLASK_ENV=dev python services/receipt_service/receipt_service/api.py

# Review Service
FLASK_ENV=dev python services/review_service/review_service/api.py

# API Gateway
FLASK_ENV=dev python services/api_gateway/api_gateway/app.py
```

2. **Test the flow**:
```bash
# Create a report via API Gateway
curl -X POST http://localhost:8080/v1/reports \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": "Test"}'
```

## API Contract Management

While services communicate via HTTP, formal API contracts should be established using:
- OpenAPI/Swagger specifications
- Schema validation
- Versioned APIs

**Future enhancements**:
- gRPC for performance-critical paths
- AsyncAPI for event definitions
- API versioning strategy

## Scalability

### Horizontal Scaling
- Each service can scale independently based on load
- Report Service: High read/write during submission periods
- Receipt Service: High during end-of-month submissions
- Review Service: Spiky during review periods

### Auto-scaling Triggers
- CPU utilization > 70%
- Request queue length
- Custom metrics (pending inbox size, OCR queue depth)

## Observability

### Logging
- Structured JSON logging with request ID correlation
- Centralized in CloudWatch Logs
- Trace ID propagation for distributed tracing

### Monitoring
- Service health checks at `/health`
- CloudWatch metrics for ECS
- Request latency tracking at API Gateway

### Tracing
- Request ID header (`X-Request-ID`) propagation
- Service-to-service call logging
- Event correlation via message IDs

## Authentication & Authorization

- JWT tokens issued by authentication service
- API Gateway validates JWT and extracts user context
- User context forwarded as headers to backend services
- RBAC permissions enforced at API Gateway

**Token Flow**:
```
Client → API Gateway (JWT validation) → Service (user context headers)
```

## Future Improvements

1. **Database per service** - Complete data ownership
2. **Event sourcing** - Immutable event log
3. **CQRS** - Command/Query Responsibility Segregation
4. **Saga pattern** - Distributed transactions for complex workflows
5. **Service mesh** - Advanced traffic management (Istio, Linkerd)
6. **GraphQL federation** - Unified API layer
7. **gRPC** - High-performance inter-service communication
