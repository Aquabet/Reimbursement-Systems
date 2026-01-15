import json
import logging
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask, g, request

from reimbursement_api.api.receipts import receipts_bp
from reimbursement_api.api.reports import reports_bp
from reimbursement_api.infrastructure.auth import jwt_manager
from reimbursement_api.infrastructure.database import db


def get_secret(secret_name):
    """Retrieve a secret from AWS Secrets Manager."""
    region_name = os.getenv("AWS_REGION", "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name, endpoint_url=endpoint_url)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in get_secret_value_response:
            return get_secret_value_response["SecretString"]
        # Binary secrets are not currently handled
        return None
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"Secret {secret_name} not found in Secrets Manager.")
        else:
            print(f"Error retrieving secret {secret_name}: {e}")
        return None


def create_app(config_name="default"):
    load_dotenv()  # Load environment variables from .env file
    app = Flask(__name__)

    # Use a different database for testing
    if config_name == "testing":
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
        app.config["TESTING"] = True
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Retrieve JWT Secret from Secrets Manager
    jwt_secret = get_secret("/reimbursement/jwt_secret_key")
    if jwt_secret:
        app.config["JWT_SECRET_KEY"] = jwt_secret
    else:
        app.logger.error("JWT_SECRET_KEY not found in Secrets Manager. Using fallback.")
        app.config["JWT_SECRET_KEY"] = os.environ.get(
            "JWT_SECRET_KEY", "fallback-jwt-secret-key"
        )  # Fallback to env var or default

    # Initialize JWTManager with the secret key
    jwt_manager.secret_key = app.config["JWT_SECRET_KEY"]

    db.init_app(app)

    # Register blueprints
    app.register_blueprint(reports_bp)
    app.register_blueprint(receipts_bp)

    # Import and register blueprints
    from reimbursement_api.api.health import health_bp

    app.register_blueprint(health_bp)

    # Setup structured logging
    setup_structured_logging(app)

    # Add request ID to all requests
    @app.before_request
    def add_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    return app


def setup_structured_logging(app):
    """Setup structured JSON logging."""
    if app.config.get("TESTING"):
        return

    # Remove default handlers
    app.logger.handlers.clear()

    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            # Build structured log record
            log_record = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "request_id": getattr(g, "request_id", None),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # Add exception info if present
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)

            return json.dumps(log_record)

    # Setup handler
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
