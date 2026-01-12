import os
import logging
from flask import Flask, request, g
from datetime import datetime

from .config import config_by_name
from .routes import reports_bp, receipts_bp, review_bp, health_bp
from .auth import JWTManager
from .proxy import ServiceProxy

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Configure logging
    configure_logging(app)

    # Register blueprints
    app.register_blueprint(reports_bp)
    app.register_blueprint(receipts_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(health_bp)

    # Request middleware for logging
    @app.before_request
    def log_request_info():
        if not request.path.startswith('/health'):
            logging.info(f"{request.method} {request.path} - {request.remote_addr}")

    # Response middleware for logging
    @app.after_request
    def log_response_info(response):
        if not request.path.startswith('/health'):
            logging.info(f"{request.method} {request.path} - {response.status_code}")
        return response

    return app

def configure_logging(app):
    """Configure structured logging."""
    level = app.config.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'dev')
    app = create_app(env)
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port, debug=(env == 'dev'))
