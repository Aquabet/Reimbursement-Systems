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
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    OCR_QUEUE_URL = os.getenv("OCR_QUEUE_URL")
    VALIDATION_QUEUE_URL = os.getenv("VALIDATION_QUEUE_URL")
    MESSAGE_BUS_BROKER = os.getenv("MESSAGE_BUS_BROKER")

    # Retrieve JWT Secret from Secrets Manager
    jwt_secret = get_secret("/reimbursement/jwt_secret_key")
    if jwt_secret:
        JWT_SECRET_KEY = jwt_secret
    else:
        logging.error("JWT_SECRET_KEY not found in Secrets Manager. Using fallback.")
        JWT_SECRET_KEY = os.getenv(
            "JWT_SECRET_KEY", "fallback-jwt-secret-key"
        )  # Fallback to env var or default


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {"dev": DevelopmentConfig, "prod": ProductionConfig}
