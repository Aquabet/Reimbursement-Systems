import os
import logging
import uuid
import json

from dotenv import load_dotenv
from flask import Flask, g, request

from reimbursement_api.api.receipts import receipts_bp
from reimbursement_api.api.reports import reports_bp
from reimbursement_api.infrastructure.database import db


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
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key")

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
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

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
