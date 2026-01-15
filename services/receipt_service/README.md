# Receipt Service

Handles receipt CRUD operations, storage management, and receipt validation results.

## API Endpoints

### Receipt Management
- `POST /v1/receipts` - Create a receipt
- `GET /v1/receipts/<id>` - Get receipt by ID
- `PUT /v1/receipts/<id>` - Update receipt
- `DELETE /v1/receipts/<id>` - Delete receipt
- `GET /v1/receipts/report/<report_id>` - Get all receipts for a report

### Receipt Status & Validation
- `GET /v1/receipts/<id>/validation` - Get validation results
- `PUT /v1/receipts/<id>/status` - Update receipt status
- `POST /v1/receipts/<id>/retry-ocr` - Retry OCR processing

## Events

Publishes events to AWS SNS Topic:
- `receipt.created` - When a new receipt is uploaded
- `receipt.ocr_completed` - When OCR processing finishes
- `receipt.validated` - When validation completes

Consumes events (e.g., from SNS subscriptions):
- `report.deleted` - Clean up receipts for deleted reports

## Security

- JWT-based authentication with secret management via AWS Secrets Manager.

## Data Model

- Manages `Receipt` and `ValidationResult` models. The `ValidationResult` model has been logically decoupled from `Receipt` to support eventual independent databases.

## Observability

- Emits structured JSON logs for better monitoring and debugging.
