import pytest
from datetime import datetime
from review_service.models import Report, AuditLog, ReviewComment


class TestReportModel:
    """Test Report model."""

    def test_report_creation(self):
        """Test report creation."""
        report = Report(
            title='Test Report',
            description='Test description',
            user_id='test-user-123',
            status='DRAFT'
        )

        assert report.title == 'Test Report'
        assert report.description == 'Test description'
        assert report.user_id == 'test-user-123'
        assert report.status == 'DRAFT'

    def test_report_to_dict(self):
        """Test report to_dict method."""
        report = Report(
            title='Test Report',
            description='Test description',
            user_id='test-user-123',
            status='SUBMITTED',
            total_receipts=5,
            total_amount=150.00
        )

        data = report.to_dict()

        assert data['title'] == 'Test Report'
        assert data['status'] == 'SUBMITTED'
        assert data['total_receipts'] == 5
        assert data['total_amount'] == 150.00
        assert 'created_at' in data

    def test_report_state_transitions(self):
        """Test report state transitions."""
        report = Report(
            title='Test Report',
            user_id='test-user-123',
            status='DRAFT'
        )

        # Simulate state transitions
        report.status = 'SUBMITTED'
        report.submitted_at = datetime.utcnow()

        assert report.status == 'SUBMITTED'
        assert report.submitted_at is not None


class TestAuditLogModel:
    """Test AuditLog model."""

    def test_audit_log_creation(self):
        """Test audit log creation."""
        log = AuditLog(
            report_id=1,
            action='SUBMITTED',
            from_status='DRAFT',
            to_status='SUBMITTED',
            user_id='test-user-123',
            user_email='test@example.com',
            notes='Report submitted for approval'
        )

        assert log.report_id == 1
        assert log.action == 'SUBMITTED'
        assert log.from_status == 'DRAFT'
        assert log.to_status == 'SUBMITTED'
        assert log.user_email == 'test@example.com'

    def test_audit_log_to_dict(self):
        """Test audit log to_dict method."""
        log = AuditLog(
            report_id=1,
            action='APPROVED',
            from_status='SUBMITTED',
            to_status='APPROVED',
            user_id='reviewer-456',
            user_email='reviewer@example.com',
            metadata='{"reviewer_notes": "All good"}'
        )

        data = log.to_dict()

        assert data['report_id'] == 1
        assert data['action'] == 'APPROVED'
        assert data['from_status'] == 'SUBMITTED'
        assert data['to_status'] == 'APPROVED'
        assert data['metadata']['reviewer_notes'] == 'All good'


class TestReviewCommentModel:
    """Test ReviewComment model."""

    def test_review_comment_creation(self):
        """Test review comment creation."""
        comment = ReviewComment(
            report_id=1,
            reviewer_id='reviewer-456',
            reviewer_email='reviewer@example.com',
            comment='Please provide more details for meal expenses',
            is_rejection_comment=False
        )

        assert comment.report_id == 1
        assert comment.reviewer_id == 'reviewer-456'
        assert comment.comment == 'Please provide more details for meal expenses'
        assert comment.is_rejection_comment is False

    def test_review_comment_to_dict(self):
        """Test review comment to_dict method."""
        comment = ReviewComment(
            report_id=1,
            reviewer_id='reviewer-456',
            reviewer_email='reviewer@example.com',
            comment='Missing receipts for transactions over $50',
            is_rejection_comment=True
        )

        data = comment.to_dict()

        assert data['report_id'] == 1
        assert data['reviewer_id'] == 'reviewer-456'
        assert data['is_rejection_comment'] is True
        assert 'created_at' in data
