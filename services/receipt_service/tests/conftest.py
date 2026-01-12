import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from receipt_service.api import create_app
from receipt_service.models import db


@pytest.fixture
def app():
    """Create test app."""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['OCR_QUEUE_URL'] = 'http://localhost:4566/test-ocr-queue'
    os.environ['VALIDATION_QUEUE_URL'] = 'http://localhost:4566/test-validation-queue'
    os.environ['MESSAGE_BUS_BROKER'] = 'local'

    app = create_app('testing')

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token."""
    return 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsInJvbGUiOiJzdWJtaXR0ZXIiLCJ1c2VyX2VtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.mock_signature'


@pytest.fixture
def mock_receipt_data():
    """Mock receipt data."""
    return {
        'report_id': 1,
        'user_id': 'test-user-123',
        'file_name': 'receipt.jpg',
        'file_path': '/tmp/receipt.jpg',
        's3_object_key': 'receipts/user123/receipt.jpg',
        'content_type': 'image/jpeg',
        'notes': 'Test receipt'
    }


@pytest.fixture
def mock_validation_result_data():
    """Mock validation result data."""
    return {
        'report_id': 1,
        'extracted_text': 'Coffee Shop $15.00 2024-01-12',
        'extracted_amount': 15.00,
        'extracted_date': '2024-01-12',
        'extracted_vendor': 'Coffee Shop',
        'extracted_category': 'Meals',
        'validation_status': 'PASS',
        'validation_rules': [{'rule': 'MealCapRule', 'status': 'PASS'}],
        'normalized_amount': 15.00,
        'warnings': [],
        'errors': []
    }


@pytest.fixture
def mock_s3():
    """Mock S3 client."""
    with patch('receipt_service.services.boto3.client') as mock_client:
        yield mock_client


@pytest.fixture
def mock_sqs():
    """Mock SQS client."""
    with patch('receipt_service.services.boto3.client') as mock_client:
        yield mock_client
