import os

from dotenv import load_dotenv
from flask import Flask

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

    db.init_app(app)

    app.register_blueprint(reports_bp)
    app.register_blueprint(receipts_bp)

    return app
