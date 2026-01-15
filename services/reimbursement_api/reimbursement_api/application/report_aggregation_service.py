from datetime import datetime, timezone

from sqlalchemy import text

from reimbursement_api.application.audit_service import AuditService
from reimbursement_api.domain.models import Report
from reimbursement_api.infrastructure.database import db


class StateTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted."""

    pass


class ReportAggregationService:
    """Service responsible for aggregating receipt results and managing report state transitions."""

    # Valid state transitions
    VALID_TRANSITIONS = {
        "DRAFT": ["SUBMITTED"],
        "SUBMITTED": ["REVIEW_PENDING", "REJECTED"],
        "REVIEW_PENDING": ["APPROVED", "REJECTED", "DRAFT"],  # Can be sent back for corrections
        "APPROVED": [],  # Terminal state
        "REJECTED": ["DRAFT"],  # Can be resubmitted after corrections
    }

    def __init__(self):
        self.audit_service = AuditService()

    def _validate_state_transition(self, current_status: str, new_status: str):
        """Validate that a state transition is allowed."""
        if current_status not in self.VALID_TRANSITIONS:
            raise StateTransitionError(f"Invalid current state: {current_status}")

        valid_next = self.VALID_TRANSITIONS[current_status]

        if new_status not in valid_next:  # type: ignore
            raise StateTransitionError(
                f"Invalid transition from {current_status} to {new_status}. "
                f"Valid transitions from {current_status} are: {', '.join(valid_next) if valid_next else 'none (terminal state)'}."  # type: ignore
            )

    def get_report_summary(self, report_id: int) -> dict:
        """Get a comprehensive summary of report including all receipt statuses."""
        report = Report.query.get_or_404(report_id)

        # Get receipt and validation data
        result = db.session.execute(
            text(
                """SELECT
                    r.id,
                    r.filename,
                    ocr.status as ocr_status,
                    vr.status as validation_status,
                    vr.normalized_amount,
                    vr.extracted_amount,
                    vr.compliance_notes
                FROM receipt r
                LEFT JOIN ocr_result ocr ON r.id = ocr.receipt_id
                LEFT JOIN validation_result vr ON r.id = vr.receipt_id
                WHERE r.report_id = :report_id"""
            ),
            {"report_id": report_id},
        ).fetchall()

        summary = {
            "report": report.to_dict(),
            "receipts": [],
            "totals": {
                "total_receipts": len(result),
                "valid_receipts": 0,
                "invalid_receipts": 0,
                "warning_receipts": 0,
                "pending_receipts": 0,
                "total_amount": 0.0,
                "total_normalized_amount": 0.0,
            },
            "ready_for_submission": False,
            "validation_errors": [],
        }

        for row in result:
            receipt_data = {
                "id": row[0],
                "filename": row[1],
                "ocr_status": row[2],
                "validation_status": row[3],
                "normalized_amount": float(row[4]) if row[4] else None,
                "extracted_amount": float(row[5]) if row[5] else None,
                "compliance_notes": row[6],
            }

            summary["receipts"].append(receipt_data)

            # Update counts
            if row[3] == "PASS":
                summary["totals"]["valid_receipts"] += 1
                if row[4]:
                    summary["totals"]["total_normalized_amount"] += float(row[4])
            elif row[3] == "FAIL":
                summary["totals"]["invalid_receipts"] += 1
                summary["validation_errors"].append(f"Receipt {row[0]} failed validation: {row[6]}")
            elif row[3] == "WARN":
                summary["totals"]["warning_receipts"] += 1
                if row[4]:
                    summary["totals"]["total_normalized_amount"] += float(row[4])
            else:
                summary["totals"]["pending_receipts"] += 1

            # Add to total amount if we have an extracted amount
            if row[5]:
                summary["totals"]["total_amount"] += float(row[5])

        summary["totals"]["total_receipts"] = len(result)

        # Check if ready for submission
        summary["ready_for_submission"] = self._check_ready_for_submission(summary)

        return summary

    def _check_ready_for_submission(self, summary: dict) -> bool:
        """Check if report is ready for submission based on receipt statuses."""
        totals = summary["totals"]

        # Must have at least one receipt
        if totals["total_receipts"] == 0:
            return False

        # Cannot submit with pending receipts
        if totals["pending_receipts"] > 0:
            return False

        # Cannot submit with failed validations
        if totals["invalid_receipts"] > 0:
            return False

        return True

    def submit_report(
        self, report_id: int, user_id: str | None = None, user_email: str | None = None
    ) -> tuple[dict, list[str]]:
        """Submit a report for approval. Returns updated report and any warnings."""
        report = Report.query.get_or_404(report_id)

        # Check current status
        if report.status != "DRAFT":
            raise StateTransitionError(f"Can only submit reports in DRAFT status. Current status: {report.status}")

        # Get report summary
        summary = self.get_report_summary(report_id)

        # Validate report can be submitted
        if not summary["ready_for_submission"]:
            errors = summary["validation_errors"]
            if summary["totals"]["pending_receipts"] > 0:
                errors.append(f"Report has {summary['totals']['pending_receipts']} pending receipts")
            raise StateTransitionError(f"Report is not ready for submission: {'; '.join(errors)}")

        # Update totals
        from_status = report.status
        report.status = "SUBMITTED"
        report.submitted_at = datetime.now(timezone.utc)
        report.total_receipts = summary["totals"]["total_receipts"]
        report.total_amount = summary["totals"]["total_amount"]
        report.valid_receipts = summary["totals"]["valid_receipts"]
        report.invalid_receipts = summary["totals"]["invalid_receipts"]
        report.warning_receipts = summary["totals"]["warning_receipts"]
        report.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Log audit entry
        self.audit_service.log_action(
            report_id=report_id,
            action="SUBMIT",
            from_status=from_status,
            to_status=report.status,
            user_id=user_id,
            user_email=user_email,
            metadata={"totals": summary["totals"]},
        )

        # Collect warnings
        warnings = []
        if summary["totals"]["warning_receipts"] > 0:
            warnings.append(
                f"Report contains {summary['totals']['warning_receipts']} receipts that require justification"
            )

        summary["report"] = report.to_dict()
        return summary, warnings

    def approve_report(
        self,
        report_id: int,
        user_id: str | None = None,
        user_email: str | None = None,
        reviewer_notes: str | None = None,
    ) -> dict:
        """Approve a submitted report."""
        report = Report.query.get_or_404(report_id)

        # Validate state transition
        self._validate_state_transition(report.status, "APPROVED")

        # Update report
        from_status = report.status
        report.status = "APPROVED"
        report.approved_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Log audit entry
        self.audit_service.log_action(
            report_id=report_id,
            action="APPROVE",
            from_status=from_status,
            to_status=report.status,
            user_id=user_id,
            user_email=user_email,
            notes=reviewer_notes,
            metadata={"approved_at": report.approved_at.isoformat()},
        )

        return report.to_dict()

    def reject_report(
        self, report_id: int, rejection_reason: str, user_id: str | None = None, user_email: str | None = None
    ) -> dict:
        """Reject a report (requires reason)."""
        if not rejection_reason:
            raise ValueError("Rejection reason is required")

        report = Report.query.get_or_404(report_id)

        # Can reject from SUBMITTED or REVIEW_PENDING
        if report.status not in ["SUBMITTED", "REVIEW_PENDING"]:
            raise StateTransitionError(
                f"Can only reject reports in SUBMITTED or REVIEW_PENDING status. Current status: {report.status}"
            )

        # Update report
        from_status = report.status
        report.status = "REJECTED"
        report.rejected_at = datetime.now(timezone.utc)
        report.rejection_reason = rejection_reason
        report.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Log audit entry
        self.audit_service.log_action(
            report_id=report_id,
            action="REJECT",
            from_status=from_status,
            to_status=report.status,
            user_id=user_id,
            user_email=user_email,
            notes=rejection_reason,
            metadata={"rejected_at": report.rejected_at.isoformat()},
        )

        return report.to_dict()

    def request_review(self, report_id: int, user_id: str | None = None, user_email: str | None = None) -> dict:
        """Move report to review pending status."""
        report = Report.query.get_or_404(report_id)

        # Can only request review from SUBMITTED
        self._validate_state_transition(report.status, "REVIEW_PENDING")

        from_status = report.status
        report.status = "REVIEW_PENDING"
        report.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Log audit entry
        self.audit_service.log_action(
            report_id=report_id,
            action="REQUEST_REVIEW",
            from_status=from_status,
            to_status=report.status,
            user_id=user_id,
            user_email=user_email,
        )

        return report.to_dict()

    def return_to_draft(self, report_id: int, user_id: str | None = None, user_email: str | None = None) -> dict:
        """Return a report to draft status (allows editing)."""
        report = Report.query.get_or_404(report_id)

        # Can return to draft from REJECTED or REVIEW_PENDING
        if report.status not in ["REJECTED", "REVIEW_PENDING"]:
            raise StateTransitionError(
                f"Can only return reports to DRAFT from REJECTED or REVIEW_PENDING status. Current status: {report.status}"
            )

        from_status = report.status
        report.status = "DRAFT"
        report.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        # Log audit entry
        self.audit_service.log_action(
            report_id=report_id,
            action="RETURN_TO_DRAFT",
            from_status=from_status,
            to_status=report.status,
            user_id=user_id,
            user_email=user_email,
        )

        return report.to_dict()

    def get_status_history(self, report_id: int) -> dict:
        """Get the status history for a report."""
        report = Report.query.get_or_404(report_id)

        history = []

        # Add current status with timestamps
        if report.created_at:
            history.append({"status": "DRAFT", "timestamp": report.created_at.isoformat(), "notes": "Report created"})

        if report.submitted_at:
            history.append(
                {
                    "status": "SUBMITTED",
                    "timestamp": report.submitted_at.isoformat(),
                    "notes": "Report submitted for approval",
                }
            )

        if report.approved_at:
            history.append(
                {"status": "APPROVED", "timestamp": report.approved_at.isoformat(), "notes": "Report approved"}
            )

        if report.rejected_at:
            history.append(
                {
                    "status": "REJECTED",
                    "timestamp": report.rejected_at.isoformat(),
                    "notes": f"Report rejected: {report.rejection_reason}",
                }
            )

        return {"report_id": report_id, "status_history": history}
