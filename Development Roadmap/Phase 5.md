# Phase 5 — Report Aggregation & State Machine

## Goals

- Aggregate receipt results at report level
- Enforce valid state transitions

## Tasks

- Implement report state machine:
- DRAFT → SUBMITTED → REVIEW_PENDING → APPROVED/REJECTED
- Aggregate receipts, extraction, and validation results
- Implement report submission endpoint

## Deliverables

- Report aggregation API
- State transition logic

## Acceptance Criteria

- Reports cannot be submitted without validation
- Report totals are accurate and deterministic
