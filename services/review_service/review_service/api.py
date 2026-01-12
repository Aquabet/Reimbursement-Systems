import os
import json
from flask import Flask, Blueprint, request, jsonify, g
from typing import Optional
from functools import wraps
import logging

from .config import config_by_name
from .models import db
from .services import ReviewService
from .auth import JWTManager
from .message_bus import get_message_bus

app = Flask(__name__)
app.config.from_object(config_by_name[os.getenv('FLASK_ENV', 'dev')])
db.init_app(app)

jwt_manager = JWTManager()
review_service = ReviewService(
    receipt_service_url=os.getenv('RECEIPT_SERVICE_URL'),
    report_service_url=os.getenv('REPORT_SERVICE_URL')
)

# Initialize message bus
message_bus = get_message_bus()
review_service.set_message_bus(message_bus)

# Register health check blueprint
from .health import health_bp
app.register_blueprint(health_bp)

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    db.init_app(app)
    return app

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

review_bp = Blueprint('review', __name__, url_prefix='/v1/review')

@review_bp.route('/inbox', methods=['GET'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def get_review_inbox():
    """Get the review inbox with pending reports."""
    try:
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        inbox_data = review_service.get_review_inbox(
            status=status, page=page, per_page=per_page
        )
        return jsonify(inbox_data), 200
    except Exception as e:
        logging.error(f"Error fetching review inbox: {e}")
        return jsonify({'error': f'Failed to fetch review inbox: {str(e)}'}), 500

@review_bp.route('/<int:report_id>', methods=['GET'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def get_report_for_review(report_id):
    """Get detailed report information for review."""
    try:
        report_details = review_service.get_report_details_for_review(report_id)
        return jsonify(report_details), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logging.error(f"Error fetching report details: {e}")
        return jsonify({'error': f'Failed to fetch report details: {str(e)}'}), 500

@review_bp.route('/<int:report_id>/approve', methods=['POST'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def approve_report(report_id):
    """Approve a submitted report."""
    try:
        data = request.get_json() or {}
        reviewer_notes = data.get('reviewer_notes')

        user_id = g.user.get('user_id')
        user_email = g.user.get('user_email')

        if not user_id or not user_email:
            return jsonify({'error': 'User information not found in token'}), 400

        report = review_service.approve_report(
            report_id=report_id,
            user_id=user_id,
            user_email=user_email,
            reviewer_notes=reviewer_notes
        )
        return jsonify({
            'report': report,
            'message': 'Report approved successfully'
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error approving report: {e}")
        return jsonify({'error': f'Failed to approve report: {str(e)}'}), 500

@review_bp.route('/<int:report_id>/reject', methods=['POST'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def reject_report(report_id):
    """Reject a submitted report."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400

        rejection_reason = data.get('rejection_reason')
        if not rejection_reason:
            return jsonify({'error': 'rejection_reason is required'}), 400

        user_id = g.user.get('user_id')
        user_email = g.user.get('user_email')

        if not user_id or not user_email:
            return jsonify({'error': 'User information not found in token'}), 400

        report = review_service.reject_report(
            report_id=report_id,
            rejection_reason=rejection_reason,
            user_id=user_id,
            user_email=user_email
        )
        return jsonify({
            'report': report,
            'message': 'Report rejected'
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logging.error(f"Error rejecting report: {e}")
        return jsonify({'error': f'Failed to reject report: {str(e)}'}), 500

reports_bp = Blueprint('reports', __name__, url_prefix='/v1/reports')

@reports_bp.route('', methods=['GET'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def list_reports():
    """List all reports (reviewer only)."""
    try:
        from .models import Report
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))

        # For reviewers/admins, show all reports
        query = Report.query
        total = query.count()
        reports = query.order_by(Report.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            'reports': [r.to_dict() for r in reports],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        logging.error(f"Error listing reports: {e}")
        return jsonify({'error': f'Failed to list reports: {str(e)}'}), 500

@reports_bp.route('/<int:report_id>', methods=['GET'])
@jwt_required
@require_roles(['reviewer', 'admin'])
def get_report(report_id):
    """Get a specific report."""
    try:
        from .models import Report
        report = Report.query.get(report_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404

        return jsonify(report.to_dict()), 200
    except Exception as e:
        logging.error(f"Error fetching report: {e}")
        return jsonify({'error': f'Failed to fetch report: {str(e)}'}), 500

@reports_bp.route('/<int:report_id>/audit', methods=['POST'])
@jwt_required
def add_audit_entry(report_id):
    """Add an audit log entry to a report."""
    try:
        data = request.get_json() or {}

        user_id = g.user.get('user_id')
        user_email = g.user.get('user_email')

        if not user_id or not user_email:
            return jsonify({'error': 'User information not found in token'}), 400

        action = data.get('action')
        if not action:
            return jsonify({'error': 'action is required'}), 400

        review_service._log_action(
            report_id=report_id,
            action=action,
            from_status=data.get('from_status'),
            to_status=data.get('to_status'),
            user_id=user_id,
            user_email=user_email,
            notes=data.get('notes'),
            metadata=data.get('metadata')
        )

        return jsonify({'message': 'Audit entry added'}), 201
    except Exception as e:
        logging.error(f"Error adding audit entry: {e}")
        return jsonify({'error': f'Failed to add audit entry: {str(e)}'}), 500

app.register_blueprint(review_bp)
app.register_blueprint(reports_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5002, debug=True)
