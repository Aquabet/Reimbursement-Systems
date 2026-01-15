# Validation Service Dead Letter Queue Setup

This document describes how to configure SQS Dead Letter Queue (DLQ) for the Validation processing pipeline to handle validation failures gracefully.

## Architecture

```
Receipt Upload → OCR Worker → Validation Worker → Database
                    ↓              ↓
              OCR DLQ      Validation DLQ
                    ↓              ↓
            Manual Review  Manual Review
```

## SQS Queue Configuration

### Primary Queue: `validation_jobs`

```bash
# Create the validation queue with DLQ configured
aws sqs create-queue \
    --queue-name reimbursement-validation-queue \
    --attributes '{
        "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:<YOUR_AWS_ACCOUNT_ID>:reimbursement-validation-queue-dlq\",\"maxReceiveCount\":\"3\"}",
        "VisibilityTimeout": "180",
        "MessageRetentionPeriod": "1209600"
    }' \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

Configuration Details:
- **VisibilityTimeout**: 180 seconds (3 minutes)
- **MessageRetentionPeriod**: 14 days (default, maximum)
- **RedrivePolicy**: Automatically move to DLQ after 3 processing attempts

### Dead Letter Queue: `validation_jobs_dlq`

```bash
# Create the Validation DLQ
aws sqs create-queue \
    --queue-name reimbursement-validation-queue-dlq \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeout": "180"
    }' \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

## Environment Variables

Add to Validation Worker `.env` file and other relevant services if they interact directly with SQS:

```bash
# Validation SQS Queue URLs
VALIDATION_QUEUE_URL="http://localstack:4566/000000000000/reimbursement-validation-queue" # LocalStack example
VALIDATION_DLQ_URL="http://localstack:4566/000000000000/reimbursement-validation-queue-dlq" # LocalStack example

# Production example (replace <YOUR_AWS_ACCOUNT_ID> and <YOUR_AWS_REGION>)
# SQS_VALIDATION_QUEUE_URL="https://sqs.<YOUR_AWS_REGION>.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-validation-queue"
# SQS_VALIDATION_DLQ_URL="https://sqs.<YOUR_AWS_REGION>.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-validation-queue-dlq"

# AWS Configuration
AWS_REGION="us-east-1"
# AWS credentials are managed via IAM Roles in production, or LocalStack in dev.
# For local testing, ensure your AWS CLI is configured or use temporary credentials.
```

## Policy Configuration

The validation service uses a policy engine with configurable rules. Current policy version: `1.0`

```python
policy_config = {
    "meal_daily_cap": 75.00,           # Maximum meals per day
    "meal_single_cap": 50.00,          # Maximum per meal receipt
    "max_receipts_per_report": 20,     # Maximum receipts per report
    "category_limits": {
        "meal": {
            "cap": 75.00,
            "requires_justification": True
        },
        "travel": {
            "cap": 200.00,
            "requires_justification": False
        },
        "fuel": {
            "cap": 100.00,
            "requires_justification": False
        },
        "office": {
            "cap": 50.00,
            "requires_justification": False
        },
        "other": {
            "cap": 25.00,
            "requires_justification": False
        },
    },
}
```

## Validation Rules Implemented

### 1. Meal Cap Rule
- **Rule ID**: `meal_cap`
- **Description**: Enforces daily and per-receipt meal spending limits
- **Daily Cap**: $75.00 per day
- **Single Receipt Cap**: $50.00 per receipt
- **Status**: FAIL if exceeds caps, WARN if justified

### 2. Receipt Count Rule
- **Rule ID**: `receipt_count_limit`
- **Description**: Limits total receipts per reimbursement report
- **Maximum**: 20 receipts per report
- **Warn Threshold**: 90% of limit (18 receipts)
- **Status**: FAIL if exceeds, WARN if approaching

### 3. Category Exception Rule
- **Rule ID**: `category_limits`
- **Description**: Category-specific limits with exceptions
- **Meal**: $75.00 cap, requires justification if exceeded
- **Travel**: $200.00 cap
- **Fuel**: $100.00 cap
- **Office**: $50.00 cap
- **Other**: $25.00 cap
- **Status**: FAIL or WARN based on justification requirement

## Validation Result Statuses

Validation results have three possible statuses:

- **PASS**: Receipt complies with all policies
- **WARN**: Receipt violates policy but may be acceptable with justification
- **FAIL**: Receipt violates policy and is not reimbursable

## Normalized Amount Calculation

The validation engine calculates a normalized reimbursement amount by applying the most restrictive rule:

```python
# Example: Meal receipt for $65
- Original Amount: $65.00
- Single meal cap: $50.00
- Normalized Amount: $50.00 (capped at policy limit)
- Status: FAIL (requires justification) or WARN if justified
```

## Error Handling Behavior

1. **First Attempt**: Message received, validation fails
   - Message returned to queue
   - Receive count: 1

2. **Second Attempt**: Message received again after VisibilityTimeout
   - Processing fails again
   - Receive count: 2

3. **Third Attempt**: Final attempt
   - Processing fails
   - Receive count: 3 (reaches maxReceiveCount)
   - **Message automatically moved to DLQ by SQS**

4. **Messages in Validation DLQ**:
   - Persist for manual review
   - Can be inspected for debugging
   - Can be reprocessed after fixing validation logic

## Monitoring

### Structured Logging

All services now emit structured JSON logs. These logs can be ingested by AWS CloudWatch Logs for centralized logging and analysis.

### Check Validation DLQ Message Count

```bash
aws sqs get-queue-attributes \
    --queue-url https://sqs.us-east-1.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-validation-queue-dlq \
    --attribute-names ApproximateNumberOfMessages \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

### CloudWatch Alarms (Recommended)

Create alarms for:
- Validation DLQ message count > 0 (indicates processing failures)
- Validation queue message age (indicates slow processing)
- Validation failure rate > threshold (indicates policy issues)
- Error logs in CloudWatch Logs (using filter patterns)

## Manual Recovery

### View Failed Validation Messages

```bash
# Pull one message from DLQ for inspection
aws sqs receive-message \
    --queue-url https://sqs.us-east-1.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-validation-queue-dlq \
    --max-number-of-messages 1 \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

### Reprocess Messages from DLQ

Option 1: Manual (one-by-one)
```python
# Read from DLQ and send back to main queue after fixing issue
# (implement a small utility script)
```

Option 2: Automated (after fixing root cause)
```bash
# Move all messages back to main queue after validation logic fix
# Then purge DLQ
aws sqs purge-queue \
    --queue-url https://sqs.us-east-1.amazonaws.com/<YOUR_AWS_ACCOUNT_ID>/reimbursement-validation-queue-dlq \
    --endpoint-url http://localhost:4566 # For LocalStack development
```

## Testing the Retry Logic

1. Upload receipt with OCR and validation workers running
2. Introduce bugs in validation logic (e.g., invalid category)
3. Verify validation fails and message retries 3 times
4. Check DLQ message count increases
5. Check validation_result table shows PENDING or error
6. Fix validation bug and restart worker
7. Manually move DLQ message back to main queue
8. Verify successful validation

## Idempotency Guarantees

The validation system ensures idempotent processing:

1. **Receipt-level Uniqueness**: ValidationResult has unique constraint on receipt_id
2. **Upsert Operations**: UPDATE with fallback INSERT prevents duplicates
3. **Policy Version Tracking**: policy_version field tracks which policy was applied
4. **Rule Tracking**: applied_rules field stores JSON array of rule names applied

This means replayed validation messages won't duplicate results - they'll update the existing validation record.

## Data Flow

```
Receipt
  └─→ OCR Worker (extracts text)
      └─→ Validation Worker (applies rules)
          └─→ ValidationResult (stores status, notes, normalized amount)
```

## Troubleshooting

**Problem**: All validations show FAIL
- ✓ Check OCR text is being extracted correctly
- ✓ Check MockMcpExtractor is parsing amounts, dates, vendors, categories
- ✓ Review policy configuration for reasonable limits

**Problem**: Normalized amount is None
- ✓ Check that extracted_amount is not None
- ✓ Verify rule results include normalized_amount
- ✓ Check ValidationResult update query

**Problem**: Validation DLQ fills up quickly
- ✓ Check database connectivity
- ✓ Review validation logic for exceptions
- ✓ Check ValidationResult table schema matches code

**Problem**: Categories always show as "other"
- ✓ Check MockMcpExtractor category extraction
- ✓ Add more vendor/category keywords to extractor
- ✓ Review OCR text quality
