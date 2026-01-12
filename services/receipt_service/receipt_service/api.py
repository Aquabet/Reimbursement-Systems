import os
import json
from flask import Flask, Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from datetime import datetime
from typing import Dict, Optional
import boto3
from functools import wraps

from .config import config_by_name
from .models import db
from .services import ReceiptService, ValidationService
from .message_bus import MessageBus

app = Flask(__name__)
app.config.from_object(config_by_name[os.getenv('FLASK_ENV', 'dev')])
db.init_app(app)

receipt_service = ReceiptService()
validation_service = ValidationService()
message_bus = MessageBus()

# Register health check blueprint
from .health import health_bp
app.register_blueprint(health_bp)

def create_app(config_name='dev'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    db.init_app(app)
    return app

def verify_jwt_token():
    """Verify JWT from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None

    try:
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None

        # For now, simple validation - in production use proper JWT library
        from .auth import JWTManager
        jwt_manager = JWTManager()
        payload = jwt_manager.verify_token(parts[1])
        return payload
    except:
        return None

def jwt_required(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        payload = verify_jwt_token()
        if not payload:
            return jsonify({'error': 'Invalid or missing token'}), 401
        g.user = payload
        return f(*args, **kwargs)
    return decorated_function

receipts_bp = Blueprint('receipts', __name__, url_prefix='/v1/receipts')

@receipts_bp.route('', methods=['POST'])
@jwt_required
def create_receipt():
    """Create a new receipt record."""
    data = request.get_json()
    required_fields = ['report_id', 'user_id', 'file_name']

    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        receipt = receipt_service.create_receipt(data)
        return jsonify(receipt.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@receipts_bp.route('/<int:receipt_id>', methods=['GET'])
@jwt_required
def get_receipt(receipt_id):
    """Get a receipt by ID."""
    receipt = receipt_service.get_receipt(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404

    return jsonify(receipt.to_dict())

@receipts_bp.route('/<int:receipt_id>', methods=['PUT'])
@jwt_required
def update_receipt(receipt_id):
    """Update a receipt."""
    data = request.get_json()
    receipt = receipt_service.update_receipt(receipt_id, data)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404

    return jsonify(receipt.to_dict())

@receipts_bp.route('/<int:receipt_id>', methods=['DELETE'])
@jwt_required
def delete_receipt(receipt_id):
    """Delete a receipt."""
    success = receipt_service.delete_receipt(receipt_id)
    if not success:
        return jsonify({'error': 'Receipt not found'}), 404

    return '', 204

@receipts_bp.route('/report/<int:report_id>', methods=['GET'])
@jwt_required
def get_receipts_by_report(report_id):
    """Get all receipts for a report."""
    receipts = receipt_service.get_receipts_by_report(report_id)
    return jsonify([r.to_dict() for r in receipts])

@receipts_bp.route('/<int:receipt_id>/validation', methods=['GET'])
@jwt_required
def get_receipt_validation(receipt_id):
    """Get validation results for a receipt."""
    result = validation_service.get_receipt_validation(receipt_id)
    if not result:
        return jsonify({'error': 'Validation result not found'}), 404

    return jsonify(result)

@receipts_bp.route('/<int:receipt_id>/status', methods=['PUT'])
@jwt_required
def update_receipt_status(receipt_id):
    """Update receipt status and OCR/validation data."""
    data = request.get_json()
    status = data.get('status')

    if not status:
        return jsonify({'error': 'Status is required'}), 400

    ocr_data = data.get('ocr_data')
    validation_data = data.get('validation_data')

    receipt = receipt_service.update_receipt_status(receipt_id, status, ocr_data, validation_data)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404

    # Publish completion events
    if status == 'OCR_COMPLETED':
        message_bus.publish('receipt.ocr_completed', {
            'receipt_id': receipt.id,
            'report_id': receipt.report_id,
            'ocr_data': ocr_data
        })
    elif status == 'VALIDATED':
        message_bus.publish('receipt.validated', {
            'receipt_id': receipt.id,
            'report_id': receipt.report_id,
            'validation_data': validation_data
        })

    return jsonify(receipt.to_dict())

@receipts_bp.route('/<int:receipt_id>/retry-ocr', methods=['POST'])
@jwt_required
def retry_ocr(receipt_id):
    """Retry OCR processing for a receipt."""
    receipt = receipt_service.retry_ocr(receipt_id)
    if not receipt:
        return jsonify({'error': 'Receipt not found'}), 404

    return jsonify(receipt.to_dict())

@receipts_bp.route('/report/<int:report_id>/validation-summary', methods=['GET'])
@jwt_required
def get_report_validation_summary(report_id):
    """Get validation summary for all receipts in a report."""
    summary = validation_service.get_report_validation_summary(report_id)
    return jsonify(summary)

app.register_blueprint(receipts_bp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)
