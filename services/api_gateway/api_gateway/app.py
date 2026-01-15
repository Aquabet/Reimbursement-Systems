import logging
import json
import uuid
from flask import Flask, request, g, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException

from .config import config_by_name
from .routes import reports_bp, receipts_bp, review_bp, health_bp

limiter = Limiter(
    key_func=get_remote_address, default_limits=["100 per minute", "1000 per hour"]
)


def create_app(config_name="dev"):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Initialize Limiter
    limiter.init_app(app)

    # Exclude health check from rate limiting
    limiter.exempt(health_bp)

    # Configure logging
    configure_logging(app)

    # Register blueprints
    app.register_blueprint(reports_bp)
    app.register_blueprint(receipts_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(health_bp)

    # Add request ID to all requests
    @app.before_request
    def add_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # Register error handler
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        response = e.get_response()
        response.data = json.dumps(
            {
                "code": e.code,
                "name": e.name,
                "description": e.description,
                "request_id": getattr(g, "request_id", None),
            }
        )
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.exception(f"Unhandled exception: {e}")
        return jsonify(
            {
                "code": 500,
                "name": "Internal Server Error",
                "description": "An unexpected error occurred.",
                "request_id": getattr(g, "request_id", None),
            }
        ), 500

    # Request middleware for logging
    @app.before_request
    def log_request_info():
        if not request.path.startswith("/health"):
            app.logger.info(
                {
                    "message": f"Request received: {request.method} {request.path}",
                    "method": request.method,
                    "path": request.path,
                    "remote_addr": request.remote_addr,
                    "request_id": getattr(g, "request_id", None),
                }
            )

    # Response middleware for logging
    @app.after_request
    def log_response_info(response):
        if not request.path.startswith("/health"):
            app.logger.info(
                {
                    "message": f"Response sent: {request.method} {request.path}",
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "request_id": getattr(g, "request_id", None),
                }
            )
        return response

    return app


def configure_logging(app):
    """Configure structured logging."""
    # Remove default handlers
    app.logger.handlers.clear()

    class StructuredFormatter(logging.Formatter):
        def format(self, record):
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
            if record.exc_info:
                log_record["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_record)

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper()))
