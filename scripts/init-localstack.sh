#!/bin/bash

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
sleep 5

# Create S3 bucket
echo "Creating S3 bucket..."
aws s3api create-bucket \
    --bucket reimbursement-receipts \
    --region us-east-1 \
    --endpoint-url http://localstack:4566

# Create OCR Queue
echo "Creating SQS OCR queue..."
aws sqs create-queue \
    --queue-name reimbursement-ocr-queue \
    --endpoint-url http://localstack:4566

# Create OCR DLQ
echo "Creating SQS OCR DLQ..."
aws sqs create-queue \
    --queue-name reimbursement-ocr-queue-dlq \
    --endpoint-url http://localstack:4566

# Create Validation Queue
echo "Creating SQS Validation queue..."
aws sqs create-queue \
    --queue-name reimbursement-validation-queue \
    --endpoint-url http://localstack:4566

# Create Validation DLQ
echo "Creating SQS Validation DLQ..."
aws sqs create-queue \
    --queue-name reimbursement-validation-queue-dlq \
    --endpoint-url http://localstack:4566

# Enable bucket versioning
echo "Enabling S3 bucket versioning..."
aws s3api put-bucket-versioning \
    --bucket reimbursement-receipts \
    --versioning-configuration Status=Enabled \
    --endpoint-url http://localstack:4566

echo "LocalStack initialization completed!"
