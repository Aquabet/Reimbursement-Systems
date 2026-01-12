import os
from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    checks = {
        'service': 'review-service',
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

    # Check external services
    external_services = ['receipt', 'report']
    for service in external_services:
        try:
            import requests
            service_url = os.getenv(f'{service.upper()}_SERVICE_URL')
            if service_url:
                response = requests.get(f"{service_url}/health", timeout=2)
                checks['checks'][f'{service}_service'] = 'healthy' if response.status_code == 200 else 'unhealthy'
            else:
                checks['checks'][f'{service}_service'] = 'skipped (no URL configured)'
        except Exception as e:
            checks['checks'][f'{service}_service'] = f'unhealthy: {str(e)}'

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
