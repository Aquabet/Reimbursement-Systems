# Dead Letter Queue Setup for OCR Service

This document describes how to configure SQS Dead Letter Queue (DLQ) for the OCR processing pipeline to handle failures gracefully.

## Architecture

```
Receipt Upload → SQS Queue (ocr_jobs) → OCR Worker → Database
                          ↓
                    Dead Letter Queue (ocr_jobs_dlq)
                          ↓
                    Manual Review / Monitoring
```

## SQS Queue Configuration

### Primary Queue: `ocr_jobs`

```bash
# Create the main queue with DLQ configured
aws sqs create-queue \
    --queue-name reimbursement-ocr-queue \
    --attributes '{
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:<YOUR_AWS_ACCOUNT_ID>:reimbursement-ocr-queue-dlq\",\"maxReceiveCount\":\"3\"}",
        "VisibilityTimeout": "180",
        "MessageRetentionPeriod": "1209600"
    }' \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

Configuration Details:
- **VisibilityTimeout**: 180 seconds (3 minutes) - should be at least 6x the expected processing time
- **MessageRetentionPeriod**: 14 days (default, maximum)
- **RedrivePolicy**: Automatically move to DLQ after 3 processing attempts

### Dead Letter Queue: `ocr_jobs_dlq`

```bash
# Create the DLQ
aws sqs create-queue \
    --queue-name reimbursement-ocr-queue-dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeout": "180"
    }' \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

## Environment Variables

Add to OCR Worker `.env` file and other relevant services (e.g., Receipt Service) if they interact directly with SQS:

```bash
# SQS Queue URLs
OCR_QUEUE_URL="http://localstack:4566/000000000000/reimbursement-ocr-queue" # LocalStack example
OCR_DLQ_URL="http://localstack:4566/000000000000/reimbursement-ocr-queue-dlq" # LocalStack example

# Production example (replace <YOUR_AWS_ACCOUNT_ID> and <YOUR_AWS_REGION>)
# SQS_QUEUE_URL="https://sqs.<YOUR_AWS_REGION>.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-ocr-queue"
# SQS_DLQ_URL="https://sqs.<YOUR_AWS_REGION>.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-ocr-queue-dlq"

# AWS Configuration
AWS_REGION="us-east-1"
# AWS credentials are managed via IAM Roles in production, or LocalStack in dev.
# For local testing, ensure your AWS CLI is configured or use temporary credentials.
```

## Error Handling Behavior

1. **First Attempt**: Message received, processing fails
   - Message returned to queue (or deleted if critical error)
   - Receive count: 1

2. **Second Attempt**: Message received again after VisibilityTimeout
   - Processing fails again
   - Receive count: 2

3. **Third Attempt**: Final attempt
   - Processing fails
   - Receive count: 3 (reaches maxReceiveCount)
   - **Message automatically moved to DLQ by SQS**

4. **Messages in DLQ**:
   - Persist for manual review
   - Can be inspected for debugging
   - Can be reprocessed by moving back to main queue

## Monitoring

### Structured Logging

All services now emit structured JSON logs. These logs can be ingested by AWS CloudWatch Logs for centralized logging and analysis.

### Check DLQ Message Count

```bash
aws sqs get-queue-attributes \
    --queue-url https://sqs.us-east-1.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-ocr-queue-dlq \
    --attribute-names ApproximateNumberOfMessages \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

### CloudWatch Alarms (Recommended)

Create alarms for:
- DLQ message count > 0 (indicates processing failures)
- Primary queue message age (indicates slow processing)
- Error logs in CloudWatch Logs (using filter patterns)

## Manual Recovery

### View Failed Messages

```bash
# Pull one message from DLQ for inspection
aws sqs receive-message \
    --queue-url https://sqs.us-east-1.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-ocr-queue-dlq \
    --max-number-of-messages 1 \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

### Reprocess Messages from DLQ

Option 1: Manual (one-by-one)
```python
# Small utility script to move messages back to main queue
# (would read from DLQ and send back to main queue)
```

Option 2: Automated (after fixing issue)
```bash
# Purge DLQ after fixing root cause and letting normal flow resume
aws sqs purge-queue \
    --queue-url https://sqs.us-east-1.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-ocr-queue-dlq \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

## Testing the Retry Logic

1. Upload a receipt with OCR worker stopped
2. Start OCR worker with an intentional bug (e.g., wrong MCP URL)
3. Verify message retries 3 times, then moves to DLQ
4. Check DLQ message count increases
5. Check ocr_result table shows FAILED status
6. Fix the bug and restart worker
7. Manually move DLQ message back to main queue
8. Verify successful processing

## Idempotency Guarantees

The system ensures idempotent OCR processing:

1. **Receipt-level Uniqueness**: Files are hashed (SHA256) before upload
2. **Duplicate Detection**: Receipts with same hash are rejected
3. **OCR Result Binding**: One OcrResult per Receipt (unique constraint)
4. **Database Upsert**: UPDATE with WHERE clause ensures no duplicate records

This means replayed messages won't duplicate results - they'll update the existing record.

## Troubleshooting

**Problem**: Messages move to DLQ immediately
- ✓ Check VisibilityTimeout is sufficient (> 6x expected processing time)
- ✓ Check OCR worker is processing within timeout

**Problem**: OCR status always shows PENDING
- ✓ Check OCR worker is running and connected to queue
- ✓ Check AWS credentials are valid
- ✓ Check Database URL is correct

**Problem**: DLQ fills up frequently
- ✓ Check OCR MCP is accessible and working
- ✓ Review OCR worker logs for error patterns
- ✓ Check file storage (local/S3) accessibility
