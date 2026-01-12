import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_gateway.auth import JWTManager


class TestJWTManager:
    """Test JWTManager."""

    @pytest.fixture
    def jwt_manager(self):
        """Create JWTManager instance."""
        return JWTManager()

    def test_create_token(self, jwt_manager):
        """Test creating JWT token."""
        token = jwt_manager.create_token(
            user_id='test-user-123',
            role='submitter',
            user_email='test@example.com'
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self, jwt_manager):
        """Test verifying valid token."""
        # Create token
        token = jwt_manager.create_token(
            user_id='test-user-123',
            role='submitter',
            user_email='test@example.com'
        )

        # Verify token
        payload = jwt_manager.verify_token(token)

        assert payload is not None
        assert payload['user_id'] == 'test-user-123'
        assert payload['role'] == 'submitter'
        assert payload['user_email'] == 'test@example.com'

    def test_verify_invalid_token(self, jwt_manager):
        """Test verifying invalid token."""
        payload = jwt_manager.verify_token('invalid.token.here')
        assert payload is None

    def test_verify_expired_token(self, jwt_manager):
        """Test verifying expired token."""
        import jwt as pyjwt
        from datetime import datetime, timedelta

        # Create expired token
        payload = {
            'user_id': 'test-user-123',
            'role': 'submitter',
            'user_email': 'test@example.com',
            'exp': datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
            'iat': datetime.utcnow() - timedelta(hours=2)
        }
        expired_token = pyjwt.encode(payload, jwt_manager.secret_key, algorithm='HS256')

        # Verify should fail
        result = jwt_manager.verify_token(expired_token)
        assert result is None
