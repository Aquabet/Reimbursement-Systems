import os
from dotenv import load_dotenv
import boto3
import logging

load_dotenv()


def get_secret(secret_name):
    """Retrieve a secret from AWS Secrets Manager."""
    region_name = os.getenv("AWS_REGION", "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")

    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager",
        region_name=region_name,
        endpoint_url=endpoint_url,
    )

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if "SecretString" in get_secret_value_response:
            return get_secret_value_response["SecretString"]
        else:
            # Binary secrets are not currently handled
            return None
    except Exception as e:
        logging.error(f"Failed to retrieve secret {secret_name}: {e}")
        return None


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    # Retrieve JWT Secret from Secrets Manager
    jwt_secret = get_secret("/reimbursement/jwt_secret_key")
    if jwt_secret:
        JWT_SECRET_KEY = jwt_secret
    else:
        logging.error("JWT_SECRET_KEY not found in Secrets Manager. Using fallback.")
        JWT_SECRET_KEY = os.getenv(
            "JWT_SECRET_KEY", "fallback-jwt-secret-key"
        )  # Fallback to env var or default
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv(
        "RATELIMIT_STORAGE_URL", "memory://"
    )  # Using memory for simplicity, can be redis://localstack:6379
    DEFAULT_RATE_LIMIT = os.getenv("DEFAULT_RATE_LIMIT", "100 per minute")

    # Service URLs
    REPORT_SERVICE_URL = os.getenv("REPORT_SERVICE_URL", "http://localhost:5000")
    RECEIPT_SERVICE_URL = os.getenv("RECEIPT_SERVICE_URL", "http://localhost:5001")
    REVIEW_SERVICE_URL = os.getenv("REVIEW_SERVICE_URL", "http://localhost:5002")
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:5003")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {"dev": DevelopmentConfig, "prod": ProductionConfig}
