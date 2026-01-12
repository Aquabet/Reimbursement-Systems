from flask import Blueprint, jsonify, request, g
from functools import wraps
from .auth import JWTManager
from .proxy import ServiceProxy
import logging

logger = logging.getLogger(__name__)

# Initialize components
jwt_manager = JWTManager()
proxy = ServiceProxy()

def jwt_required(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401

        try:
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization header format'}), 401

            token = parts[1]
            payload = jwt_manager.verify_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401

            g.user = payload
            return f(*args, **kwargs)
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
    return decorated_function

def require_roles(allowed_roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                return jsonify({'error': 'Authentication required'}), 401

            user_role = g.user.get('role')
            if not user_role:
                return jsonify({'error': 'Role not found in token'}), 403

            if user_role not in allowed_roles:
                return jsonify({'error': f'Insufficient permissions. Required roles: {allowed_roles}'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Blueprints
reports_bp = Blueprint('reports', __name__, url_prefix='/v1/reports')
receipts_bp = Blueprint('receipts', __name__, url_prefix='/v1/receipts')
review_bp = Blueprint('review', __name__, url_prefix='/v1/review')
health_bp = Blueprint('health', __name__, url_prefix='/health')

# Routes

# Reports
@reports_bp.route('', methods=['POST'])
@jwt_required
def create_report():
    """Create a report (forwards to report service)."""
    data, status, headers = proxy.forward_request('reports', '/v1/reports')
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>', methods=['GET'])
@jwt_required
def get_report(report_id):
    """Get a report."""
    data, status, headers = proxy.forward_request('reports', f'/v1/reports/{report_id}')
    return jsonify(data), status, headers

@reports_bp.route('', methods=['GET'])
@jwt_required
def list_reports():
    """List reports."""
    data, status, headers = proxy.forward_request('reports', '/v1/reports', timeout=10)
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>/submit', methods=['POST'])
@jwt_required
def submit_report(report_id):
    """Submit a report."""
    data, status, headers = proxy.forward_request('reports', f'/v1/reports/{report_id}/submit')
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>/summary', methods=['GET'])
@jwt_required
def get_report_summary(report_id):
    """Get report summary."""
    data, status, headers = proxy.forward_request('reports', f'/v1/reports/{report_id}/summary')
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>/approve', methods=['POST'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def approve_report(report_id):
    """Approve a report."""
    data, status, headers = proxy.forward_request('review', f'/v1/review/{report_id}/approve')
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>/reject', methods=['POST'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def reject_report(report_id):
    """Reject a report."""
    data, status, headers = proxy.forward_request('review', f'/v1/review/{report_id}/reject')
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>/audit-trail', methods=['GET'])
@jwt_required
def get_audit_trail(report_id):
    """Get audit trail for report."""
    data, status, headers = proxy.forward_request('reports', f'/v1/reports/{report_id}/audit-trail')
    return jsonify(data), status, headers

@reports_bp.route('/<int:report_id>/status-history', methods=['GET'])
@jwt_required
def get_status_history(report_id):
    """Get status history for report."""
    data, status, headers = proxy.forward_request('reports', f'/v1/reports/{report_id}/status-history')
    return jsonify(data), status, headers

# Receipts
@receipts_bp.route('', methods=['POST'])
@jwt_required
def create_receipt():
    """Create a receipt."""
    data, status, headers = proxy.forward_request('receipts', '/v1/receipts')
    return jsonify(data), status, headers

@receipts_bp.route('/<int:receipt_id>', methods=['GET'])
@jwt_required
def get_receipt(receipt_id):
    """Get a receipt."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/{receipt_id}')
    return jsonify(data), status, headers

@receipts_bp.route('/<int:receipt_id>', methods=['PUT'])
@jwt_required
def update_receipt(receipt_id):
    """Update a receipt."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/{receipt_id}')
    return jsonify(data), status, headers

@receipts_bp.route('/<int:receipt_id>', methods=['DELETE'])
@jwt_required
def delete_receipt(receipt_id):
    """Delete a receipt."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/{receipt_id}')
    return jsonify(data), status, headers

@receipts_bp.route('/report/<int:report_id>', methods=['GET'])
@jwt_required
def get_receipts_by_report(report_id):
    """Get receipts for a report."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/report/{report_id}')
    return jsonify(data), status, headers

@receipts_bp.route('/<int:receipt_id>/validation', methods=['GET'])
@jwt_required
def get_receipt_validation(receipt_id):
    """Get receipt validation."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/{receipt_id}/validation')
    return jsonify(data), status, headers

@receipts_bp.route('/<int:receipt_id>/status', methods=['PUT'])
@jwt_required
def update_receipt_status(receipt_id):
    """Update receipt status."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/{receipt_id}/status')
    return jsonify(data), status, headers

@receipts_bp.route('/<int:receipt_id>/retry-ocr', methods=['POST'])
@jwt_required
def retry_ocr(receipt_id):
    """Retry OCR for receipt."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/{receipt_id}/retry-ocr')
    return jsonify(data), status, headers

@receipts_bp.route('/report/<int:report_id>/validation-summary', methods=['GET'])
@jwt_required
def get_report_validation_summary(report_id):
    """Get validation summary for report."""
    data, status, headers = proxy.forward_request('receipts', f'/v1/receipts/report/{report_id}/validation-summary')
    return jsonify(data), status, headers

# Review endpoints
@review_bp.route('/inbox', methods=['GET'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def get_review_inbox():
    """Get review inbox."""
    data, status, headers = proxy.forward_request('review', '/v1/review/inbox')
    return jsonify(data), status, headers

@review_bp.route('/<int:report_id>', methods=['GET'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def get_report_for_review(report_id):
    """Get report for review."""
    data, status, headers = proxy.forward_request('review', f'/v1/review/{report_id}')
    return jsonify(data), status, headers

# Health checks
@health_bp.route('', methods=['GET'])
def health_check():
    """Health check for API Gateway."""
    return jsonify({'status': 'healthy', 'service': 'api-gateway'}), 200

@health_bp.route('/services', methods=['GET'])
def services_health():
    """Get health status of all backend services."""
    from .service_discovery import service_discovery

    health_status = service_discovery.get_all_health()

    all_healthy = all(health_status.values())
    status_code = 200 if all_healthy else 503

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'services': health_status
    }), status_code
