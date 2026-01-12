# Phase 3 — Asynchronous OCR Processing

## Goals

- Offload OCR to async workers
- Ensure idempotent, retry-safe execution

## Tasks

- Provision SQS queue: `ocr_jobs`
- Publish OCR jobs after receipt upload
- Implement OCR worker service:
- Consume SQS messages
- Execute OCR MCP
- Persist extraction results
- Implement DLQ and retry strategy

## Deliverables

- OCR worker service
- Extraction results table

## Acceptance Criteria

- OCR jobs execute asynchronously
- Replayed jobs do not duplicate results
