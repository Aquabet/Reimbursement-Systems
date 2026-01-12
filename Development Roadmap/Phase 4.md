# Phase 4 — Validation & Data Analysis MCP

## Goals

- Enforce reimbursement policies
- Detect anomalies and normalize amounts

## Tasks

- Provision SQS queue: `validation_jobs`
- Implement validation worker:
- Load policy version
- Apply rule engine
- Generate validation results
- Implement rule modules:
- Meal caps
- Receipt count limits
- Category-based exceptions

## Deliverables

- Validation worker
- Policy engine implementation

## Acceptance Criteria

- PASS/WARN/FAIL results produced
- Normalized reimbursement amounts calculated
