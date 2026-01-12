# Phase 2 — Receipt Upload & Storage

## Goals

- Enable receipt file uploads
- Track receipt lifecycle

## Tasks

- Implement receipt upload endpoint:
- `POST /v1/receipts/upload`
- Store receipt metadata in database
- Implement storage abstraction:
- Local filesystem (dev)
- Amazon S3 (prod)
- Add receipt hashing for duplicate detection

## Deliverables

- Receipt upload API
- Storage abstraction layer

## Acceptance Criteria

- Uploaded files are retrievable
- Duplicate uploads are detected or deduplicated
