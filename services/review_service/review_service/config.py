import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    MESSAGE_BUS_BROKER = os.getenv('MESSAGE_BUS_BROKER')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    RECEIPT_SERVICE_URL = os.getenv('RECEIPT_SERVICE_URL', 'http://localhost:5001')
    REPORT_SERVICE_URL = os.getenv('REPORT_SERVICE_URL', 'http://localhost:5000')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'dev': DevelopmentConfig,
    'prod': ProductionConfig
}
