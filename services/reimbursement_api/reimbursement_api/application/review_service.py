from typing import Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import joinedload
from reimbursement_api.infrastructure.database import db
from reimbursement_api.domain.models import Report
from reimbursement_api.application.report_aggregation_service import (
    ReportAggregationService,
    StateTransitionError,
)


class ReviewService:
    """Service for managing the review workflow and reviewer inbox."""

    def __init__(self):
        self.aggregation_service = ReportAggregationService()

    def get_review_inbox(
        self,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        assigned_to: Optional[str] = None,
    ) -> Dict:
        """
        Get reports that are pending review.

        Args:
            status: Filter by report status (e.g., 'SUBMITTED', 'REVIEW_PENDING')
            page: Page number (1-indexed)
            per_page: Number of items per page
            assigned_to: Filter by assigned reviewer (optional)

        Returns:
            Dictionary with paginated reports and metadata
        """
        # Default to showing reports that need review
        if not status:
            status_filter = ["SUBMITTED", "REVIEW_PENDING"]
        else:
            status_filter = [status]

        query = (
            Report.query.filter(Report.status.in_(status_filter))
            .options(joinedload(Report.receipts))
            .order_by(Report.submitted_at.desc().nulls_last())
        )

        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        reports_data = []
        for report in pagination.items:
            report_dict = report.to_dict()
            report_dict["receipt_count"] = len(report.receipts)
            report_dict["pending_for_hours"] = (
                (datetime.utcnow() - report.submitted_at).total_seconds() / 3600
                if report.submitted_at
                else None
            )
            reports_data.append(report_dict)

        return {
            "reports": reports_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
            "filters": {
                "status": status,
                "assigned_to": assigned_to,
            },
        }

    def get_report_details_for_review(self, report_id: int) -> Dict:
        """
        Get detailed information about a report for review purposes.
        Includes audit trail and validation details.

        Args:
            report_id: The ID of the report

        Returns:
            Dictionary with report details, summary, and audit trail
        """
        # Get report with receipts
        report = Report.query.options(joinedload(Report.receipts)).get_or_404(report_id)

        # Get report summary with validation results
        summary = self.aggregation_service.get_report_summary(report_id)

        # Get audit trail
        audit_trail = self.aggregation_service.audit_service.get_audit_trail(report_id)

        return {
            "report": report.to_detailed_dict(),
            "summary": summary,
            "audit_trail": audit_trail,
        }

    def approve_report_with_review(
        self,
        report_id: int,
        reviewer_id: str,
        reviewer_email: str,
        approval_notes: Optional[str] = None,
    ) -> Tuple[Dict, str]:
        """
        Approve a report as part of the review process.
        Records reviewer information in audit log.

        Args:
            report_id: The ID of the report
            reviewer_id: ID of the reviewer
            reviewer_email: Email of the reviewer
            approval_notes: Optional approval notes

        Returns:
            Tuple of (updated_report, success_message)
        """
        # Approve the report
        updated_report = self.aggregation_service.approve_report(
            report_id=report_id,
            user_id=reviewer_id,
            user_email=reviewer_email,
            reviewer_notes=approval_notes,
        )

        message = "Report approved successfully"
        if approval_notes:
            message += f". Notes: {approval_notes}"

        return updated_report, message

    def reject_report_with_review(
        self,
        report_id: int,
        reviewer_id: str,
        reviewer_email: str,
        rejection_reason: str,
        rejection_notes: Optional[str] = None,
    ) -> Tuple[Dict, str]:
        """
        Reject a report as part of the review process.
        Records reviewer information and reason in audit log.

        Args:
            report_id: The ID of the report
            reviewer_id: ID of the reviewer
            reviewer_email: Email of the reviewer
            rejection_reason: Reason for rejection
            rejection_notes: Additional rejection notes

        Returns:
            Tuple of (updated_report, rejection_message)
        """
        if not rejection_reason:
            raise ValueError("Rejection reason is required")

        # Combine reason and notes
        full_reason = rejection_reason
        if rejection_notes:
            full_reason += f"\n\nAdditional notes: {rejection_notes}"

        # Reject the report
        updated_report = self.aggregation_service.reject_report(
            report_id=report_id,
            rejection_reason=full_reason,
            user_id=reviewer_id,
            user_email=reviewer_email,
        )

        message = f"Report rejected. Reason: {rejection_reason}"

        return updated_report, message

    def request_changes(
        self,
        report_id: int,
        reviewer_id: str,
        reviewer_email: str,
        change_requests: str,
    ) -> Tuple[Dict, str]:
        """
        Request changes on a report and return it to draft status.

        Args:
            report_id: The ID of the report
            reviewer_id: ID of the reviewer
            reviewer_email: Email of the reviewer
            change_requests: Description of changes needed

        Returns:
            Tuple of (updated_report, message)
        """
        if not change_requests:
            raise ValueError("Change requests description is required")

        # Return to draft (this will log the audit entry)
        updated_report = self.aggregation_service.return_to_draft(
            report_id=report_id,
            user_id=reviewer_id,
            user_email=reviewer_email,
        )

        # Log additional details about changes requested
        self.aggregation_service.audit_service.log_action(
            report_id=report_id,
            action="REQUEST_CHANGES",
            from_status="REVIEW_PENDING",
            to_status="DRAFT",
            user_id=reviewer_id,
            user_email=reviewer_email,
            notes=change_requests,
            metadata={"changes_requested": True},
        )

        message = f"Report returned to draft. Changes requested: {change_requests}"

        return updated_report, message

    def get_review_statistics(self) -> Dict:
        """
        Get statistics about reports in the review queue.

        Returns:
            Dictionary with review statistics
        """
        # Count reports by status
        submitted_count = Report.query.filter_by(status="SUBMITTED").count()
        review_pending_count = Report.query.filter_by(status="REVIEW_PENDING").count()
        approved_count = Report.query.filter_by(status="APPROVED").count()
        rejected_count = Report.query.filter_by(status="REJECTED").count()

        # Calculate average review time for approved reports
        result = db.session.execute(
            text(
                """SELECT
                    AVG(EXTRACT(EPOCH FROM (approved_at - submitted_at))/3600) as avg_hours
                FROM report
                WHERE status = 'APPROVED'
                AND submitted_at IS NOT NULL
                AND approved_at IS NOT NULL"""
            )
        ).fetchone()

        avg_review_hours = float(result[0]) if result and result[0] else 0.0

        return {
            "queue_summary": {
                "submitted": submitted_count,
                "review_pending": review_pending_count,
                "approved": approved_count,
                "rejected": rejected_count,
                "total_pending": submitted_count + review_pending_count,
            },
            "performance": {
                "average_review_hours": round(avg_review_hours, 2),
            },
        }
