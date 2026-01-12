import pytest
from datetime import datetime
from receipt_service.models import Receipt, ValidationResult


class TestReceiptModel:
    """Test Receipt model."""

    def test_receipt_creation(self):
        """Test receipt creation."""
        receipt = Receipt(
            report_id=1,
            user_id='test-user-123',
            file_name='receipt.jpg',
            s3_object_key='receipts/test.jpg',
            status='UPLOADED'
        )

        assert receipt.report_id == 1
        assert receipt.user_id == 'test-user-123'
        assert receipt.file_name == 'receipt.jpg'
        assert receipt.status == 'UPLOADED'

    def test_receipt_to_dict(self):
        """Test receipt to_dict method."""
        receipt = Receipt(
            report_id=1,
            user_id='test-user-123',
            file_name='receipt.jpg',
            amount=15.50,
            vendor='Test Vendor'
        )

        data = receipt.to_dict()

        assert data['report_id'] == 1
        assert data['user_id'] == 'test-user-123'
        assert data['file_name'] == 'receipt.jpg'
        assert data['amount'] == 15.50
        assert data['vendor'] == 'Test Vendor'

    def test_receipt_to_detailed_dict(self):
        """Test receipt to_detailed_dict method."""
        receipt = Receipt(
            report_id=1,
            user_id='test-user-123',
            file_name='receipt.jpg',
            validation_results='{"status": "PASS"}'
        )

        data = receipt.to_detailed_dict()

        assert data['report_id'] == 1
        assert data['validation_results']['status'] == 'PASS'


class TestValidationResultModel:
    """Test ValidationResult model."""

    def test_validation_result_creation(self):
        """Test validation result creation."""
        result = ValidationResult(
            receipt_id=1,
            report_id=1,
            extracted_text='Test receipt $15.00',
            validation_status='PASS'
        )

        assert result.receipt_id == 1
        assert result.report_id == 1
        assert result.validation_status == 'PASS'

    def test_validation_result_to_dict(self):
        """Test validation result to_dict method."""
        result = ValidationResult(
            receipt_id=1,
            report_id=1,
            extracted_text='Test receipt $15.00',
            extracted_amount=15.00,
            extracted_date=datetime(2024, 1, 12).date(),
            extracted_vendor='Test Vendor',
            validation_status='PASS',
            validation_rules='[{"rule": "test", "status": "PASS"}]',
            warnings='["warning1"]',
            errors='[]'
        )

        data = result.to_dict()

        assert data['receipt_id'] == 1
        assert data['extracted_amount'] == 15.00
        assert data['validation_status'] == 'PASS'
        assert len(data['validation_rules']) == 1
        assert len(data['warnings']) == 1
        assert len(data['errors']) == 0
