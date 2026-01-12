import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from review_service.api import create_app
from review_service.models import db


@pytest.fixture
def app():
    """Create test app."""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['SECRET_KEY'] = 'test-secret'
    os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'
    os.environ['RECEIPT_SERVICE_URL'] = 'http://mock-receipt-service'
    os.environ['REPORT_SERVICE_URL'] = 'http://mock-report-service'

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
    """Mock JWT token for submitter."""
    return 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTEyMyIsInJvbGUiOiJzdWJtaXR0ZXIiLCJ1c2VyX2VtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImV4cCI6OTk5OTk5OTk5OX0.mock_signature'


@pytest.fixture
def mock_jwt_token_reviewer():
    """Mock JWT token for reviewer."""
    return 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoicmV2aWV3ZXItNTY3Iiwicm9sZSI6InJldmlld2VyIiwidXNlcl9lbWFpbCI6InJldmlld2VyQGV4YW1wbGUuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ.mock_signature_reviewer'


@pytest.fixture
def mock_jwt_token_admin():
    """Mock JWT token for admin."""
    return 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYWRtaW4tOTk5Iiwicm9sZSI6ImFkbWluIiwidXNlcl9lbWFpbCI6ImFkbWluQGV4YW1wbGUuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ.mock_signature_admin'


@pytest.fixture
def mock_report_data():
    """Mock report data."""
    return {
        'title': 'Test Report',
        'description': 'Test description',
        'user_id': 'test-user-123',
        'total_receipts': 0,
        'total_amount': 0.0
    }


@pytest.fixture
def mock_approval_data():
    """Mock approval data."""
    return {
        'reviewer_notes': 'Approved for payment'
    }


@pytest.fixture
def mock_rejection_data():
    """Mock rejection data."""
    return {
        'rejection_reason': 'Missing receipts for meals over $50'
    }
