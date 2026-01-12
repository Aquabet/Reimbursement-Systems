from flask import Blueprint, jsonify, current_app
from datetime import datetime
import boto3
import os

health_bp = Blueprint('health', __name__, url_prefix='/health')

@health_bp.route('', methods=['GET'])
def health_check():
    """Health check endpoint."""
    checks = {
        'service': 'report-service',
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }

    # Check database
    try:
        from reimbursement_api.domain.models import db
        db.session.execute('SELECT 1')
        checks['checks']['database'] = 'healthy'
    except Exception as e:
        checks['checks']['database'] = f'unhealthy: {str(e)}'
        checks['status'] = 'unhealthy'

    # Message queue health would be checked here if needed

    status_code = 200 if checks['status'] == 'healthy' else 503
    return jsonify(checks), status_code

@health_bp.route('/ready', methods=['GET'])
def ready_check():
    """Readiness check for Kubernetes."""
    return jsonify({'status': 'ready'}), 200

@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes."""
    return jsonify({'status': 'alive'}), 200
