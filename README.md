# Backend Design Document

## AWS-Based Reimbursement Automation System

### 1. Overview

The AWS-Based Reimbursement Automation System is a backend platform that automates expense reimbursement workflows. It processes uploaded receipts using OCR and data analysis pipelines to extract structured data, validate expenses against company policies, detect anomalies, and route submissions for automated or manual review.

The system is designed with:

- Strong separation of concerns
- Clear domain boundaries
- Asynchronous processing for compute-heavy tasks
- A modular architecture that can evolve into microservices

### 2. Goals and Non-Goals

#### 2.1 Goals

- Maintainability: Clean code organization, multi-file structure, and domain isolation
- Scalability: Asynchronous workers and horizontal scaling
- Extensibility: Policy rules and OCR engines are pluggable
- Reliability: Idempotent processing and retry-safe workers
- Observability: Structured logging, metrics, and tracing
- Security: Least-privilege access and auditability

#### 2.2 Non-Goals

- Frontend/UI implementation details
- Vendor lock-in to a specific OCR engine
- Payroll or accounting system integrations

### 3. Domain Model

#### 3.1 Core Entities

- User – Expense submitter or reviewer
- ExpenseReport – A logical grouping of expense submissions
- Receipt – Uploaded receipt metadata and processing state
- ExtractionResult – OCR and structured data extraction output
- Policy – Reimbursement rules and constraints
- ValidationResult – Rule evaluation outcome
- ReviewTask – Manual approval or rejection workflow
- AuditLog – Immutable record of critical actions

### 4. High-Level Architecture

#### 4.1 Logical Services

| Service | Responsibility |
| --- | --- |
| API Gateway / BFF | Unified API entry point |
| Report Service | Expense report lifecycle and aggregation |
| Receipt Service | Receipt metadata and processing state |
| OCR Worker (MCP) | OCR text extraction and structuring |
| Validation Worker (MCP) | Policy enforcement and anomaly detection |
| Review Service | Human review workflows |
| Notification Service | Email or chat notifications |

#### 4.2 Communication Model

- Synchronous: REST (JSON over HTTP)
- Asynchronous: SQS for OCR and validation jobs
- Event-driven: SNS for cross-service signals

### 5. Deployment Architecture

#### 5.1 Compute

- API Services: ECS Fargate (long-running, scalable)
- Workers:
  - Lambda (lightweight OCR/validation)
  - ECS Workers (heavy dependencies or ML models)

#### 5.2 Storage

- Database: MySQL (Amazon RDS)
- File Storage: Amazon S3
- Queue: Amazon SQS
- Cache: Redis

### 6. Code Organization

#### 6.1 Monorepo Layout

```text
repo/
├─ services/
│  ├─ report-service/
│  ├─ receipt-service/
│  ├─ review-service/
│  ├─ ocr-worker/
│  ├─ validation-worker/
│
├─ libs/
│  ├─ common/          # logging, config, errors
│  ├─ contracts/       # API & event schemas
│  ├─ db/              # migrations and db utilities
│
├─ infra/
│  ├─ terraform/
│  ├─ docker/
│
├─ docs/
│  └─ backend-design.md
```

#### 6.2 Service Internal Structure (Flask Example)

```text
report-service/
├─ app/
│  ├─ main.py              # create_app()
│  ├─ config.py
│  ├─ api/
│  │  └─ v1/
│  │     └─ reports.py     # HTTP controllers
│  ├─ application/
│  │  ├─ commands/
│  │  ├─ queries/
│  │  └─ services/
│  ├─ domain/
│  │  ├─ models/
│  │  ├─ policies/
│  │  └─ events/
│  ├─ infrastructure/
│  │  ├─ db/
│  │  ├─ messaging/
│  │  └─ observability/
│
├─ migrations/
├─ tests/
├─ Dockerfile
└─ pyproject.toml
```

Key Principle:
Business logic never lives in HTTP routes. Routes only validate input and delegate to application services.

### 7. API Design (Examples)

#### 7.1 Receipt Service

- `POST /v1/receipts/upload`
- `GET /v1/receipts/{receipt_id}`
- `POST /v1/receipts/{receipt_id}/reprocess`

#### 7.2 Report Service

- `POST /v1/reports`
- `POST /v1/reports/{report_id}/submit`
- `GET /v1/reports/{report_id}`

#### 7.3 Review Service

- `GET /v1/reviews/inbox`
- `POST /v1/reviews/{task_id}/approve`
- `POST /v1/reviews/{task_id}/reject`

### 8. Asynchronous Processing & Idempotency

#### 8.1 Queues

- `ocr_jobs`
- `validation_jobs`
- `review_events`

#### 8.2 Idempotency Strategy

- Each job includes an `idempotency_key`
- Workers verify processing stage before writing
- Retries are safe and deterministic
- Dead Letter Queues (DLQ) for failed jobs

### 9. MCP Design

#### 9.1 OCR MCP

Input:

- Receipt ID
- File location

Output:

- Merchant
- Date
- Total amount
- Line items
- Confidence score
- Raw text

#### 9.2 Validation MCP

Input:

- ExtractionResult
- Policy version

Rules:

- Daily meal cap
- Receipt count limits
- Category-based exceptions
- Duplicate detection
- Anomaly detection

Output:

```json
{
  "status": "PASS | WARN | FAIL",
  "normalized_amount": 50.00,
  "reasons": [
    {
      "code": "MEAL_CAP_EXCEEDED",
      "severity": "WARN"
    }
  ]
}
```

### 10. Database Design (MySQL)

#### Core Tables

- `users`
- `expense_reports`
- `receipts`
- `extraction_results`
- `validation_results`
- `review_tasks`
- `audit_logs`

Indexes are applied to:

- Receipt hashes (duplicate detection)
- Report and receipt status fields
- Time-based queries

### 11. Security

- JWT-based authentication (AWS Secrets Manager for key management)
- Role-based access control (RBAC)
- Encrypted storage (S3, RDS, KMS)
- Immutable audit logs
- Request rate limiting (implemented in API Gateway)

### 12. Observability

- Logging: JSON structured logs (implemented in API Gateway)
- Tracing: OpenTelemetry
- Metrics:
  - OCR latency
  - Validation error rates
  - Queue backlog
  - Review SLA

### 13. CI/CD

- GitHub Actions for CI/CD pipelines (build, test, deploy to staging)
- Linting and static typing
- Unit and integration tests
- Performance tests (using Locust)
- OpenAPI schema validation
- Alembic migration checks
- Blue/green or rolling ECS deployments

### 14. Evolution Path

#### Phase 1 – Modular Monolith

- Single API service
- Shared database
- Async OCR/validation workers

#### Phase 2 – Microservices

- Separate Report / Receipt / Review services
- Service-owned data (logical decoupling initiated for Receipt Service)

#### Phase 3 – Event Driven

- EventBridge-based workflows
- Policy versioning and experimentation


### 15. Deliverables

- `docs/backend-design.md`
- OpenAPI specifications
- Terraform modules
- Docker Compose for local development
- Per-service README files

### 16. Deployment Tutorials

#### 16.1 Development Environment Deployment

The development environment uses Docker Compose for quick startup and management.

**Prerequisites:**

*   Docker Desktop (or Docker Engine and Docker Compose)

**Deployment Steps:**

1.  **Clone the project repository:**
    ```bash
    git clone https://github.com/Aquabet/Reimbursement-Systems.git
    cd Reimbursement-Systems
    ```
2.  **Start services:**
    Run the following command to start all microservices, MySQL database, and LocalStack (simulated AWS services):
    ```bash
    docker-compose up --build
    ```
    The `-d` option can be used to run services in the background: `docker-compose up -d --build`
3.  **Verify services:**
    After all services have started, you can verify their status by accessing the following health check endpoints:
    *   API Gateway: `http://localhost:8080/health`
    *   Report Service: `http://localhost:5000/health`
    *   Receipt Service: `http://localhost:5001/health`
    *   Review Service: `http://localhost:5002/health`
    *   LocalStack (S3): `http://localhost:4566/health` (Check if S3, SQS, SNS, Secrets Manager are working correctly)

#### 16.2 Production Environment Deployment (AWS with Terraform)

Production environment deployment is based on the AWS cloud platform and Terraform for Infrastructure as Code (IaC) management.

**Prerequisites:**

*   AWS account and credentials configured with administrator permissions
*   Terraform CLI
*   AWS CLI
*   Docker CLI

**Overview of Deployment Steps:**

1.  **Configure AWS credentials:**
    Ensure your AWS CLI is configured with credentials. Terraform will use these credentials for deployment.
    ```bash
    aws configure
    ```
2.  **Initialize Terraform:**
    Navigate to the `infrastructure/terraform` directory and initialize Terraform.
    ```bash
    cd infrastructure/terraform
    terraform init
    ```
3.  **Plan deployment:**
    Terraform will display a plan of resources to be created, modified, or destroyed.
    ```bash
    terraform plan -var-file="staging/staging.tfvars"
    ```
    (Use `-var-file` to specify environment configuration files, e.g., `staging/staging.tfvars` or `production/production.tfvars`)
4.  **Apply deployment:**
    After confirming the plan, apply the Terraform plan to deploy resources.
    ```bash
    terraform apply -var-file="staging/staging.tfvars"
    ```
    Enter `yes` to confirm.
5.  **Build and push Docker images:**
    For each microservice, you need to build its Docker image and push it to AWS ECR (Elastic Container Registry).
    ```bash
    # Example: Report Service
    cd ../../services/reimbursement_api
    aws ecr get-login-password --region <your-aws-region> | docker login --username AWS --password-stdin <your-aws-account-id>.dkr.ecr.<your-aws-region>.amazonaws.com
    docker build -t report-service .
    docker tag report-service:latest <your-aws-account-id>.dkr.ecr.<your-aws-region>.amazonaws.com/report-service:latest
    docker push <your-aws-account-id>.dkr.ecr.<your-aws-region>.amazonaws.com/report-service:latest
    ```
    Repeat this step for all services.
6.  **Update ECS Services:**
    Once Docker images are pushed to ECR, ECS services will automatically update to pull the latest images (if CI/CD is configured).
    If manual updates are needed, you can use the AWS console or AWS CLI.

#### 16.3 CI/CD Automated Deployment

The project is configured with GitHub Actions CI/CD pipelines (located in `.github/workflows/`). When code is pushed to the `master` branch or a pull request is submitted, build and test steps are automatically triggered. These pipelines can be extended in the future to include automated deployment steps to staging/production environments.

**Future Enhancements:**

*   Integrate AWS CodePipeline and CodeBuild for a fully automated deployment process.
*   Configure blue/green deployment or canary release strategies.
