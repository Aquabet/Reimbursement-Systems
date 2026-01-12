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
    --queue-name ocr_jobs \
    --attributes '{
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:123456789012:ocr_jobs_dlq\",\"maxReceiveCount\":\"3\"}",
        "VisibilityTimeout": "180",
        "MessageRetentionPeriod": "1209600"
    }'
```

Configuration Details:
- **VisibilityTimeout**: 180 seconds (3 minutes) - should be at least 6x the expected processing time
- **MessageRetentionPeriod**: 14 days (default, maximum)
- **RedrivePolicy**: Automatically move to DLQ after 3 processing attempts

### Dead Letter Queue: `ocr_jobs_dlq`

```bash
# Create the DLQ
aws sqs create-queue \
    --queue-name ocr_jobs_dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeout": "180"
    }'
```

## Environment Variables

Add to both OCR Worker and Reimbursement API `.env` files:

```bash
# SQS Queue URLs
SQS_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789012/ocr_jobs"
SQS_DLQ_URL="https://sqs.us-east-1.amazonaws.com/123456789012/ocr_jobs_dlq"

# AWS Configuration
AWS_REGION="us-east-1"
AWS_ACCESS_KEY_ID="your-access-key"
AWS_SECRET_ACCESS_KEY="your-secret-key"
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

### Check DLQ Message Count

```bash
aws sqs get-queue-attributes \
    --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/ocr_jobs_dlq \
    --attribute-names ApproximateNumberOfMessages
```

### CloudWatch Alarms (Recommended)

Create alarms for:
- DLQ message count > 0 (indicates processing failures)
- Primary queue message age (indicates slow processing)

## Manual Recovery

### View Failed Messages

```bash
# Pull one message from DLQ for inspection
aws sqs receive-message \
    --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/ocr_jobs_dlq \
    --max-number-of-messages 1
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
    --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/ocr_jobs_dlq
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
