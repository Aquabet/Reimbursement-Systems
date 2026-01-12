import os
from functools import wraps
from typing import Callable, Optional, List
import jwt
from flask import request, jsonify, g
from datetime import datetime, timedelta


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user is not authorized."""
    pass


class RBAC:
    """Role-Based Access Control definitions."""

    # Role definitions
    SUBMITTER = "submitter"
    REVIEWER = "reviewer"
    ADMIN = "admin"

    # Permission definitions
    PERMISSIONS = {
        SUBMITTER: [
            "create_report",
            "view_own_report",
            "submit_report",
            "view_own_receipts",
        ],
        REVIEWER: [
            "view_all_reports",
            "approve_report",
            "reject_report",
            "request_changes",
            "view_review_inbox",
        ],
        ADMIN: [
            # Inherits all permissions
            "create_report",
            "view_own_report",
            "submit_report",
            "view_own_receipts",
            "view_all_reports",
            "approve_report",
            "reject_report",
            "request_changes",
            "view_review_inbox",
            "manage_users",
            "override_validation",
            "delete_report",
        ],
    }

    @classmethod
    def has_permission(cls, user_role: str, permission: str) -> bool:
        """Check if a user role has a specific permission."""
        if user_role not in cls.PERMISSIONS:
            return False

        return permission in cls.PERMISSIONS[user_role]

    @classmethod
    def get_all_permissions(cls, user_role: str) -> List[str]:
        """Get all permissions for a user role."""
        return cls.PERMISSIONS.get(user_role, [])


class JWTManager:
    """JWT token manager for authentication."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")
        self.algorithm = "HS256"

    def create_token(self, user_id: str, email: str, role: str, expires_in: int = 3600) -> str:
        """
        Create a JWT token.

        Args:
            user_id: Unique user identifier
            email: User email
            role: User role (submitter, reviewer, admin)
            expires_in: Token expiration in seconds (default: 1 hour)

        Returns:
            JWT token string
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload

        Raises:
            AuthenticationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    def get_user_from_token(self) -> Optional[dict]:
        """Extract user info from the Authorization header."""
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        # Expected format: "Bearer <token>"
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]

        try:
            return self.verify_token(token)
        except AuthenticationError:
            return None


# Global JWT manager instance
jwt_manager = JWTManager()


def jwt_required(optional: bool = False) -> Callable:
    """
    Decorator to require JWT authentication.

    Args:
        optional: If True, authentication is optional

    Returns:
        Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_info = jwt_manager.get_user_from_token()

            if user_info is None and not optional:
                return jsonify({"error": "Authentication required"}), 401

            # Store user info in Flask global for use in the request
            g.user = user_info

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_permission(permission: str, optional: bool = False) -> Callable:
    """
    Decorator to require a specific permission.

    Args:
        permission: The required permission
        optional: If True, permission check is optional

    Returns:
        Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Call jwt_required first
            auth_decorator = jwt_required(optional=optional)
            auth_result = auth_decorator(lambda: None)()

            if auth_result is not None:
                return auth_result

            # Check permission
            user = g.user
            if not user and not optional:
                return jsonify({"error": "User information not found"}), 401

            if user:
                user_role = user.get("role")

                if not RBAC.has_permission(user_role, permission):
                    return (
                        jsonify(
                            {
                                "error": f"Insufficient permissions. Required: {permission}",
                                "role": user_role,
                            }
                        ),
                        403,
                    )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_roles(roles: List[str], optional: bool = False) -> Callable:
    """
    Decorator to require one of multiple roles.

    Args:
        roles: List of allowed roles
        optional: If True, role check is optional

    Returns:
        Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Call jwt_required first
            auth_decorator = jwt_required(optional=optional)
            auth_result = auth_decorator(lambda: None)()

            if auth_result is not None:
                return auth_result

            # Check role
            user = g.user
            if not user and not optional:
                return jsonify({"error": "User information not found"}), 401

            if user:
                user_role = user.get("role")

                if user_role not in roles:
                    return (
                        jsonify(
                            {
                                "error": f"Role not allowed. Allowed roles: {', '.join(roles)}",
                                "role": user_role,
                            }
                        ),
                        403,
                    )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_current_user() -> Optional[dict]:
    """Get the current authenticated user."""
    return getattr(g, "user", None)


def get_current_user_id() -> Optional[str]:
    """Get the current user ID."""
    user = get_current_user()
    return user.get("user_id") if user else None


def get_current_user_email() -> Optional[str]:
    """Get the current user email."""
    user = get_current_user()
    return user.get("email") if user else None


def get_current_user_role() -> Optional[str]:
    """Get the current user role."""
    user = get_current_user()
    return user.get("role") if user else None
