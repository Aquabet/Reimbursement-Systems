import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from review_service.services import ReviewService
from review_service.models import Report, AuditLog, ReviewComment, db


class TestReviewService:
    """Test ReviewService."""

    @pytest.fixture
    def review_service(self):
        """Create ReviewService instance."""
        service = ReviewService(
            receipt_service_url='http://mock-receipt-service',
            report_service_url='http://mock-report-service'
        )
        return service

    def test_get_review_inbox(self, review_service):
        """Test getting review inbox."""
        # Create test reports
        report1 = Report(
            title='Report 1',
            user_id='user-123',
            status='SUBMITTED',
            total_receipts=3,
            total_amount=75.00,
            submitted_at=datetime.utcnow()
        )
        report2 = Report(
            title='Report 2',
            user_id='user-456',
            status='REVIEW_PENDING',
            total_receipts=5,
            total_amount=150.00,
            submitted_at=datetime.utcnow()
        )

        db.session.add(report1)
        db.session.add(report2)
        db.session.commit()

        # Mock external service calls
        with patch('review_service.services.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'total_receipts': 3}
            mock_get.return_value.status_code = 200

            inbox = review_service.get_review_inbox()

            assert 'reports' in inbox
            assert len(inbox['reports']) == 2
            assert inbox['reports'][0]['status'] == 'SUBMITTED'

    def test_get_review_inbox_with_status_filter(self, review_service):
        """Test getting review inbox with status filter."""
        # Create test reports with different statuses
        submitted_report = Report(
            title='Submitted Report',
            user_id='user-123',
            status='SUBMITTED',
            total_receipts=3
        )
        approved_report = Report(
            title='Approved Report',
            user_id='user-456',
            status='APPROVED',
            total_receipts=5
        )

        db.session.add(submitted_report)
        db.session.add(approved_report)
        db.session.commit()

        # Mock external service calls
        with patch('review_service.services.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'total_receipts': 3}
            mock_get.return_value.status_code = 200

            # Filter by SUBMITTED
            inbox = review_service.get_review_inbox(status='SUBMITTED')

            assert len(inbox['reports']) == 1
            assert inbox['reports'][0]['status'] == 'SUBMITTED'

    def test_get_report_details_for_review(self, review_service):
        """Test getting report details for review."""
        report = Report(
            title='Test Report',
            user_id='user-123',
            status='SUBMITTED',
            total_receipts=3,
            total_amount=75.00
        )
        db.session.add(report)
        db.session.commit()

        # Mock external service calls
        with patch('review_service.services.requests.get') as mock_get:
            mock_get.return_value.json.return_value = [
                {'id': 1, 'amount': 25.00},
                {'id': 2, 'amount': 50.00}
            ]
            mock_get.return_value.status_code = 200

            report_details = review_service.get_report_details_for_review(report.id)

            assert report_details['title'] == 'Test Report'
            assert report_details['status'] == 'SUBMITTED'
            assert len(report_details['receipts']) == 2

    def test_approve_report(self, review_service):
        """Test approving a report."""
        report = Report(
            title='Test Report',
            user_id='user-123',
            status='SUBMITTED',
            total_receipts=3,
            total_amount=75.00
        )
        db.session.add(report)
        db.session.commit()

        # Mock message bus
        review_service.message_bus = Mock()
        review_service.message_bus.publish = Mock()

        # Approve the report
        approved = review_service.approve_report(
            report_id=report.id,
            user_id='reviewer-456',
            user_email='reviewer@example.com',
            reviewer_notes='All checks passed'
        )

        assert approved['status'] == 'APPROVED'
        assert approved['approved_at'] is not None

        # Verify audit log was created
        audit_logs = AuditLog.query.filter_by(report_id=report.id).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == 'APPROVED'
        assert audit_logs[0].from_status == 'SUBMITTED'
        assert audit_logs[0].to_status == 'APPROVED'

    def test_reject_report(self, review_service):
        """Test rejecting a report."""
        report = Report(
            title='Test Report',
            user_id='user-123',
            status='SUBMITTED',
            total_receipts=3,
            total_amount=200.00
        )
        db.session.add(report)
        db.session.commit()

        # Mock message bus
        review_service.message_bus = Mock()
        review_service.message_bus.publish = Mock()

        # Reject the report
        rejected = review_service.reject_report(
            report_id=report.id,
            rejection_reason='Meal expenses exceed policy limit',
            user_id='reviewer-456',
            user_email='reviewer@example.com'
        )

        assert rejected['status'] == 'REJECTED'
        assert rejected['rejection_reason'] == 'Meal expenses exceed policy limit'

        # Verify audit log was created
        audit_logs = AuditLog.query.filter_by(report_id=report.id).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == 'REJECTED'

        # Verify review comment was created
        comments = ReviewComment.query.filter_by(report_id=report.id).all()
        assert len(comments) == 1
        assert comments[0].is_rejection_comment is True

    def test_approve_non_submitted_report_fails(self, review_service):
        """Test that approving non-submitted report fails."""
        report = Report(
            title='Test Report',
            user_id='user-123',
            status='DRAFT',
            total_receipts=3
        )
        db.session.add(report)
        db.session.commit()

        with pytest.raises(ValueError) as exc_info:
            review_service.approve_report(
                report_id=report.id,
                user_id='reviewer-456',
                user_email='reviewer@example.com'
            )

        assert 'Only SUBMITTED or REVIEW_PENDING reports can be approved' in str(exc_info.value)

    def test_reject_without_reason_fails(self, review_service):
        """Test that rejecting without reason fails."""
        report = Report(
            title='Test Report',
            user_id='user-123',
            status='SUBMITTED',
            total_receipts=3
        )
        db.session.add(report)
        db.session.commit()

        with pytest.raises(ValueError) as exc_info:
            review_service.reject_report(
                report_id=report.id,
                rejection_reason='',  # Empty reason
                user_id='reviewer-456',
                user_email='reviewer@example.com'
            )

        assert 'Rejection reason is required' in str(exc_info.value)

    def test_update_report_summary(self, review_service):
        """Test updating report summary with receipt data."""
        report = Report(
            title='Test Report',
            user_id='user-123',
            status='DRAFT',
            total_receipts=0,
            total_amount=0.0
        )
        db.session.add(report)
        db.session.commit()

        updated = review_service.update_report_summary(
            report_id=report.id,
            total_receipts=5,
            total_amount=250.00
        )

        assert updated['total_receipts'] == 5
        assert updated['total_amount'] == 250.00
