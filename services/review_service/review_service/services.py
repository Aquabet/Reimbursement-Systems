import requests
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ReviewService:
    """Handles review workflow and approval/rejection actions."""

    def __init__(self, receipt_service_url: str = None, report_service_url: str = None):
        self.receipt_service_url = receipt_service_url
        self.report_service_url = report_service_url
        self.message_bus = None

    def set_message_bus(self, message_bus):
        """Set the message bus for event publishing."""
        self.message_bus = message_bus

    def get_review_inbox(self, status: Optional[str] = None,
                         page: int = 1, per_page: int = 20) -> Dict:
        """Get reports pending review."""
        from .models import Report, db

        # Query reports with SUBMITTED or REVIEW_PENDING status
        query = Report.query.filter(Report.status.in_(['SUBMITTED', 'REVIEW_PENDING']))

        if status:
            query = query.filter_by(status=status)

        # Apply pagination
        total = query.count()
        reports = query.order_by(Report.submitted_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        # Get receipt summaries for each report
        enriched_reports = []
        for report in reports:
            report_data = report.to_dict()

            # Fetch validation summary from Receipt Service
            try:
                receipt_summary = self._get_report_receipts_summary(report.id)
                report_data['receipt_summary'] = receipt_summary
            except Exception as e:
                logger.error(f"Failed to fetch receipts for report {report.id}: {e}")
                report_data['receipt_summary'] = {'total_receipts': 0}

            enriched_reports.append(report_data)

        return {
            'reports': enriched_reports,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }

    def get_report_details_for_review(self, report_id: int) -> Dict:
        """Get detailed report information for review purposes."""
        from .models import Report, db

        report = Report.query.get(report_id)
        if not report:
            raise ValueError("Report not found")

        report_details = report.to_detailed_dict()

        # Fetch receipts from Receipt Service
        try:
            receipts_data = self._get_report_receipts(report_id)
            report_details['receipts'] = receipts_data
        except Exception as e:
            logger.error(f"Failed to fetch receipts for report {report_id}: {e}")
            report_details['receipts'] = []

        # Get validation summary
        try:
            validation_summary = self._get_report_validation_summary(report_id)
            report_details['validation_summary'] = validation_summary
        except Exception as e:
            logger.error(f"Failed to fetch validation summary for report {report_id}: {e}")
            report_details['validation_summary'] = {}

        # Get audit trail
        try:
            from .models import AuditLog
            audit_logs = AuditLog.query.filter_by(report_id=report_id).order_by(AuditLog.created_at.desc()).all()
            report_details['audit_trail'] = [log.to_dict() for log in audit_logs]
        except Exception as e:
            logger.error(f"Failed to fetch audit trail for report {report_id}: {e}")
            report_details['audit_trail'] = []

        return report_details

    def approve_report(self, report_id: int, user_id: str, user_email: str,
                       reviewer_notes: Optional[str] = None) -> Dict:
        """Approve a submitted report."""
        from .models import Report, AuditLog, db

        report = Report.query.get(report_id)
        if not report:
            raise ValueError("Report not found")

        # Validate state transition
        if report.status != 'SUBMITTED' and report.status != 'REVIEW_PENDING':
            raise ValueError("Only SUBMITTED or REVIEW_PENDING reports can be approved")

        # Update report status
        old_status = report.status
        report.status = 'APPROVED'
        report.approved_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()

        # Log action
        self._log_action(
            report_id=report_id,
            action='APPROVED',
            from_status=old_status,
            to_status='APPROVED',
            user_id=user_id,
            user_email=user_email,
            notes=reviewer_notes
        )

        db.session.commit()

        # Publish event
        if self.message_bus:
            self.message_bus.publish('report.approved', {
                'report_id': report_id,
                'user_id': user_id,
                'user_email': user_email,
                'approved_at': report.approved_at.isoformat(),
                'reviewer_notes': reviewer_notes
            })

        return report.to_dict()

    def reject_report(self, report_id: int, rejection_reason: str,
                     user_id: str, user_email: str) -> Dict:
        """Reject a submitted report."""
        from .models import Report, AuditLog, ReviewComment, db

        if not rejection_reason:
            raise ValueError("Rejection reason is required")

        report = Report.query.get(report_id)
        if not report:
            raise ValueError("Report not found")

        # Validate state transition
        if report.status not in ['SUBMITTED', 'REVIEW_PENDING']:
            raise ValueError("Only SUBMITTED or REVIEW_PENDING reports can be rejected")

        # Update report status
        old_status = report.status
        report.status = 'REJECTED'
        report.rejection_reason = rejection_reason
        report.rejected_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()

        # Add review comment
        comment = ReviewComment(
            report_id=report_id,
            reviewer_id=user_id,
            reviewer_email=user_email,
            comment=rejection_reason,
            is_rejection_comment=True
        )
        db.session.add(comment)

        # Log action
        self._log_action(
            report_id=report_id,
            action='REJECTED',
            from_status=old_status,
            to_status='REJECTED',
            user_id=user_id,
            user_email=user_email,
            notes=rejection_reason
        )

        db.session.commit()

        # Publish event
        if self.message_bus:
            self.message_bus.publish('report.rejected', {
                'report_id': report_id,
                'user_id': user_id,
                'user_email': user_email,
                'rejected_at': report.rejected_at.isoformat(),
                'rejection_reason': rejection_reason
            })

        return report.to_dict()

    def _log_action(self, report_id: int, action: str, from_status: Optional[str],
                   to_status: Optional[str], user_id: str, user_email: str,
                   notes: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log an action to the audit trail."""
        from .models import AuditLog, db

        log = AuditLog(
            report_id=report_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            user_id=user_id,
            user_email=user_email,
            notes=notes,
            metadata=json.dumps(metadata) if metadata else None
        )
        db.session.add(log)

    def _get_report_receipts_summary(self, report_id: int) -> Dict:
        """Fetch receipt summary from Receipt Service."""
        if not self.receipt_service_url:
            logger.warning("Receipt service URL not configured")
            return {'total_receipts': 0}

        url = f"{self.receipt_service_url}/v1/receipts/report/{report_id}/validation-summary"

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch receipt summary: {e}")
            return {'total_receipts': 0}

    def _get_report_receipts(self, report_id: int) -> List[Dict]:
        """Fetch all receipts for a report from Receipt Service."""
        if not self.receipt_service_url:
            logger.warning("Receipt service URL not configured")
            return []

        url = f"{self.receipt_service_url}/v1/receipts/report/{report_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch receipts: {e}")
            return []

    def _get_report_validation_summary(self, report_id: int) -> Dict:
        """Fetch validation summary from Receipt Service."""
        if not self.receipt_service_url:
            logger.warning("Receipt service URL not configured")
            return {}

        url = f"{self.receipt_service_url}/v1/receipts/report/{report_id}/validation-summary"

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch validation summary: {e}")
            return {}

    def update_report_summary(self, report_id: int, total_receipts: int, total_amount: float) -> Dict:
        """Update report summary with receipt aggregation data."""
        from .models import Report, db

        report = Report.query.get(report_id)
        if not report:
            raise ValueError("Report not found")

        report.total_receipts = total_receipts
        report.total_amount = total_amount
        report.updated_at = datetime.utcnow()

        db.session.commit()
        return report.to_dict()
