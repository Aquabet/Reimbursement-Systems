import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

class JWTManager:
    """JWT token management."""

    def __init__(self):
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'dev-secret')

    def create_token(self, user_id: str, role: str, user_email: str) -> str:
        """Create a JWT token for a user."""
        payload = {
            'user_id': user_id,
            'role': role,
            'user_email': user_email,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return {
                'user_id': payload.get('user_id'),
                'role': payload.get('role'),
                'user_email': payload.get('user_email')
            }
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
