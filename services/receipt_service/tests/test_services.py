import pytest
from unittest.mock import Mock, patch, MagicMock
from receipt_service.services import ReceiptService, ValidationService
from receipt_service.models import Receipt, ValidationResult


class TestReceiptService:
    """Test ReceiptService."""

    @pytest.fixture
    def receipt_service(self):
        """Create ReceiptService instance."""
        return ReceiptService()

    def test_create_receipt(self, receipt_service, mock_receipt_data):
        """Test creating a receipt."""
        with patch('receipt_service.services.MessageBus') as mock_bus:
            receipt = receipt_service.create_receipt(mock_receipt_data)

            assert receipt.report_id == mock_receipt_data['report_id']
            assert receipt.user_id == mock_receipt_data['user_id']
            assert receipt.file_name == mock_receipt_data['file_name']

    def test_get_receipt(self, receipt_service):
        """Test getting a receipt."""
        # Create a receipt first
        with patch('receipt_service.services.MessageBus'):
            receipt = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test.jpg'
            })

            # Get the receipt
            retrieved = receipt_service.get_receipt(receipt.id)
            assert retrieved.id == receipt.id

    def test_get_receipts_by_report(self, receipt_service):
        """Test getting receipts by report ID."""
        with patch('receipt_service.services.MessageBus'):
            receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test1.jpg'
            })
            receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test2.jpg'
            })

            receipts = receipt_service.get_receipts_by_report(1)
            assert len(receipts) == 2

    def test_update_receipt(self, receipt_service):
        """Test updating a receipt."""
        with patch('receipt_service.services.MessageBus'):
            receipt = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test.jpg'
            })

            updated = receipt_service.update_receipt(receipt.id, {
                'notes': 'Updated notes',
                'amount': 25.50
            })

            assert updated.notes == 'Updated notes'
            assert updated.amount == 25.50

    def test_delete_receipt(self, receipt_service):
        """Test deleting a receipt."""
        with patch('receipt_service.services.MessageBus'):
            receipt = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test.jpg',
                's3_object_key': 'test-bucket/test.jpg'
            })

            # Mock S3 delete
            with patch('receipt_service.services.boto3.client') as mock_s3:
                success = receipt_service.delete_receipt(receipt.id)
                assert success is True

    def test_update_receipt_status(self, receipt_service):
        """Test updating receipt status."""
        with patch('receipt_service.services.MessageBus'):
            receipt = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test.jpg'
            })

            updated = receipt_service.update_receipt_status(
                receipt.id,
                'OCR_COMPLETED',
                ocr_data={'amount': 15.00, 'vendor': 'Test'}
            )

            assert updated.status == 'OCR_COMPLETED'
            assert updated.amount == 15.00
            assert updated.vendor == 'Test'

    def test_create_validation_result(self, receipt_service, mock_validation_result_data):
        """Test creating validation result."""
        result = receipt_service.create_validation_result(1, mock_validation_result_data)

        assert result.receipt_id == 1
        assert result.validation_status == 'PASS'
        assert result.extracted_amount == 15.00

    def test_get_validation_result(self, receipt_service, mock_validation_result_data):
        """Test getting validation result."""
        receipt_service.create_validation_result(1, mock_validation_result_data)

        result = receipt_service.get_validation_result(1)
        assert result is not None
        assert result.receipt_id == 1

    def test_update_validation_result(self, receipt_service, mock_validation_result_data):
        """Test updating validation result."""
        receipt_service.create_validation_result(1, mock_validation_result_data)

        updated = receipt_service.update_validation_result(1, {
            'validation_status': 'WARN',
            'warnings': ['High amount']
        })

        assert updated.validation_status == 'WARN'
        assert 'High amount' in updated.warnings

    def test_retry_ocr(self, receipt_service):
        """Test retrying OCR."""
        with patch('receipt_service.services.MessageBus'):
            receipt = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test.jpg'
            })

            with patch('receipt_service.services.boto3.client') as mock_sqs:
                retried = receipt_service.retry_ocr(receipt.id)

                assert retried.status == 'PENDING_OCR'
                assert retried.id == receipt.id


class TestValidationService:
    """Test ValidationService."""

    @pytest.fixture
    def validation_service(self):
        """Create ValidationService instance."""
        return ValidationService()

    def test_get_receipt_validation(self, validation_service):
        """Test getting receipt validation result."""
        # Create receipt and validation result
        receipt_service = ReceiptService()

        with patch('receipt_service.services.MessageBus'):
            receipt = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test.jpg'
            })

            receipt_service.create_validation_result(receipt.id, {
                'report_id': 1,
                'validation_status': 'PASS',
                'extracted_amount': 10.00
            })

            result = validation_service.get_receipt_validation(receipt.id)
            assert result is not None
            assert result['validation_status'] == 'PASS'

    def test_get_report_validation_summary(self, validation_service):
        """Test getting report validation summary."""
        receipt_service = ReceiptService()

        with patch('receipt_service.services.MessageBus'):
            # Create receipts
            receipt1 = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test1.jpg'
            })
            receipt2 = receipt_service.create_receipt({
                'report_id': 1,
                'user_id': 'test-user',
                'file_name': 'test2.jpg'
            })

            # Create validation results
            receipt_service.create_validation_result(receipt1.id, {
                'report_id': 1,
                'validation_status': 'PASS',
                'normalized_amount': 15.00
            })
            receipt_service.create_validation_result(receipt2.id, {
                'report_id': 1,
                'validation_status': 'WARN',
                'normalized_amount': 25.00,
                'warnings': ['High meal expense']
            })

            summary = validation_service.get_report_validation_summary(1)

            assert summary['total_receipts'] == 2
            assert summary['validated_receipts'] == 2
            assert summary['passed_receipts'] == 1
            assert summary['warning_receipts'] == 1
            assert summary['total_amount'] == 15.00
