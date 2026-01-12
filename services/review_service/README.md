# Review Service

Manages the review workflow, approver inbox, and approval actions for reports.

## API Endpoints

### Review Workflow
- `GET /v1/review/inbox` - Get review inbox with pending reports
- `GET /v1/review/<report_id>` - Get report details for review
- `POST /v1/review/<report_id>/approve` - Approve a report
- `POST /v1/review/<report_id>/reject` - Reject a report

### Reports
- `GET /v1/reports` - List all reports (reviewer only)
- `GET /v1/reports/<id>` - Get report details
- `POST /v1/reports/<id>/audit` - Add audit log entry

## Events

Publishes events to Message Bus:
- `report.approved` - When a report is approved
- `report.rejected` - When a report is rejected

Consumes events:
- `report.submitted` - Notify reviewers of new submission
