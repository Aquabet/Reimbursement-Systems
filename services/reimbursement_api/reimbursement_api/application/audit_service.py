import json
from typing import Dict, Optional
from datetime import datetime
from reimbursement_api.domain.models import AuditLog, db


class AuditService:
    """Service for creating and querying immutable audit logs."""

    @staticmethod
    def log_action(
        report_id: int,
        action: str,
        from_status: Optional[str] = None,
        to_status: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> AuditLog:
        """
        Create an immutable audit log entry for a report action.

        Args:
            report_id: The ID of the report being acted upon
            action: The action being performed (e.g., 'SUBMIT', 'APPROVE', 'REJECT')
            from_status: The status before the action
            to_status: The status after the action
            user_id: ID of the user performing the action
            user_email: Email of the user performing the action
            notes: Optional notes/reason for the action
            metadata: Optional dictionary of additional context

        Returns:
            The created AuditLog entry
        """
        audit_log = AuditLog(
            report_id=report_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            user_id=user_id,
            user_email=user_email,
            notes=notes,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        db.session.add(audit_log)
        db.session.commit()

        return audit_log

    @staticmethod
    def get_audit_trail(report_id: int) -> list[Dict]:
        """
        Get the complete audit trail for a report.

        Args:
            report_id: The ID of the report

        Returns:
            List of audit log entries in chronological order
        """
        audit_logs = (
            AuditLog.query.filter_by(report_id=report_id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )

        return [log.to_dict() for log in audit_logs]

    @staticmethod
    def get_audit_trail_paginated(
        report_id: int, page: int = 1, per_page: int = 50
    ) -> Dict:
        """
        Get paginated audit trail for a report.

        Args:
            report_id: The ID of the report
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            Dictionary with audit logs and pagination info
        """
        query = AuditLog.query.filter_by(report_id=report_id).order_by(
            AuditLog.created_at.asc()
        )

        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "audit_logs": [log.to_dict() for log in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

    @staticmethod
    def get_all_audit_logs(
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 100,
    ) -> Dict:
        """
        Get all audit logs with optional filtering.

        Args:
            user_id: Filter by user ID
            action: Filter by action type
            from_date: Filter logs from this date
            to_date: Filter logs up to this date
            page: Page number (1-indexed)
            per_page: Number of items per page

        Returns:
            Dictionary with filtered audit logs and pagination info
        """
        query = AuditLog.query.order_by(AuditLog.created_at.desc())

        if user_id:
            query = query.filter_by(user_id=user_id)

        if action:
            query = query.filter_by(action=action)

        if from_date:
            query = query.filter(AuditLog.created_at >= from_date)

        if to_date:
            query = query.filter(AuditLog.created_at <= to_date)

        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "audit_logs": [log.to_dict() for log in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

    @staticmethod
    def verify_audit_integrity(report_id: int) -> bool:
        """
        Verify the integrity of audit logs for a report.
        Checks for any gaps or inconsistencies in the audit trail.

        Args:
            report_id: The ID of the report

        Returns:
            True if audit trail is intact, False otherwise
        """
        audit_logs = (
            AuditLog.query.filter_by(report_id=report_id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )

        if not audit_logs:
            return True

        # Check that each log's to_status matches the next log's from_status
        for i in range(len(audit_logs) - 1):
            current_log = audit_logs[i]
            next_log = audit_logs[i + 1]

            # Skip if either status is None (e.g., initial creation)
            if current_log.to_status is None or next_log.from_status is None:
                continue

            if current_log.to_status != next_log.from_status:
                return False

        return True
