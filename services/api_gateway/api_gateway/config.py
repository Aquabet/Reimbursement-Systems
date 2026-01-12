import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    # Service URLs
    REPORT_SERVICE_URL = os.getenv('REPORT_SERVICE_URL', 'http://localhost:5000')
    RECEIPT_SERVICE_URL = os.getenv('RECEIPT_SERVICE_URL', 'http://localhost:5001')
    REVIEW_SERVICE_URL = os.getenv('REVIEW_SERVICE_URL', 'http://localhost:5002')
    AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:5003')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}
