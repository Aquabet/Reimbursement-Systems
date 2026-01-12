from flask import Blueprint, jsonify, current_app
import os
import boto3
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    checks = {
        'service': 'receipt-service',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }

    # Check database
    try:
        from .models import db
        db.session.execute('SELECT 1')
        checks['checks']['database'] = 'healthy'
    except Exception as e:
        checks['checks']['database'] = f'unhealthy: {str(e)}'
        checks['status'] = 'unhealthy'

    # Check S3
    try:
        s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        bucket_name = os.getenv('S3_BUCKET_NAME')
        if bucket_name:
            s3.head_bucket(Bucket=bucket_name)
            checks['checks']['s3'] = 'healthy'
        else:
            checks['checks']['s3'] = 'skipped (no bucket configured)'
    except Exception as e:
        checks['checks']['s3'] = f'unhealthy: {str(e)}'

    # Check SQS
    try:
        queue_url = os.getenv('OCR_QUEUE_URL')
        if queue_url:
            sqs = boto3.client('sqs', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            sqs.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            checks['checks']['sqs'] = 'healthy'
        else:
            checks['checks']['sqs'] = 'skipped (no queue configured)'
    except Exception as e:
        checks['checks']['sqs'] = f'unhealthy: {str(e)}'

    status_code = 200 if checks['status'] == 'healthy' else 503
    return jsonify(checks), status_code

@health_bp.route('/health/ready', methods=['GET'])
def ready_check():
    """Readiness check for Kubernetes."""
    return jsonify({'status': 'ready'}), 200

@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes."""
    return jsonify({'status': 'alive'}), 200
