import boto3
import grequests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
import logging
from .models import db, Receipt, ValidationResult

logger = logging.getLogger(__name__)

class ReceiptService:
    def create_receipt(self, data: Dict) -> Receipt:
        receipt = Receipt(
            report_id=data['report_id'],
            user_id=data['user_id'],
            file_name=data['file_name'],
            file_path=data.get('file_path'),
            s3_object_key=data.get('s3_object_key'),
            content_type=data.get('content_type'),
            notes=data.get('notes', '')
        )
        db.session.add(receipt)
        db.session.commit()

        # Publish receipt.created event
        self._publish_event('receipt.created', {
            'receipt_id': receipt.id,
            'report_id': receipt.report_id,
            'user_id': receipt.user_id,
            'file_name': receipt.file_name,
            's3_object_key': receipt.s3_object_key
        })

        return receipt

    def get_receipt(self, receipt_id: int) -> Optional[Receipt]:
        return Receipt.query.get(receipt_id)

    def get_receipts_by_report(self, report_id: int) -> List[Receipt]:
        return Receipt.query.filter_by(report_id=report_id).all()

    def update_receipt(self, receipt_id: int, data: Dict) -> Optional[Receipt]:
        receipt = self.get_receipt(receipt_id)
        if not receipt:
            return None

        for key, value in data.items():
            if hasattr(receipt, key):
                setattr(receipt, key, value)

        receipt.updated_at = datetime.utcnow()
        db.session.commit()
        return receipt

    def delete_receipt(self, receipt_id: int) -> bool:
        receipt = self.get_receipt(receipt_id)
        if not receipt:
            return False

        # Delete from S3 if exists
        if receipt.s3_object_key:
            try:
                s3 = boto3.client('s3')
                bucket_name = receipt.s3_object_key.split('/')[0]
                key = '/'.join(receipt.s3_object_key.split('/')[1:])
                s3.delete_object(Bucket=bucket_name, Key=key)
            except Exception as e:
                logger.error(f"Failed to delete S3 object: {e}")

        db.session.delete(receipt)
        db.session.commit()

        # Publish receipt.deleted event
        self._publish_event('receipt.deleted', {
            'receipt_id': receipt_id,
            'report_id': receipt.report_id
        })

        return True

    def update_receipt_status(self, receipt_id: int, status: str,
                             ocr_data: Optional[Dict] = None,
                             validation_data: Optional[Dict] = None) -> Optional[Receipt]:
        receipt = self.get_receipt(receipt_id)
        if not receipt:
            return None

        receipt.status = status

        if ocr_data:
            receipt.amount = ocr_data.get('amount')
            receipt.expense_date = ocr_data.get('expense_date')
            receipt.vendor = ocr_data.get('vendor')
            receipt.category = ocr_data.get('category')
            receipt.ocr_completed_at = datetime.utcnow()

        if validation_data:
            receipt.validation_completed_at = datetime.utcnow()

        receipt.updated_at = datetime.utcnow()
        db.session.commit()

        return receipt

    def create_validation_result(self, receipt_id: int, data: Dict) -> ValidationResult:
        result = ValidationResult(
            receipt_id=receipt_id,
            report_id=data['report_id'],
            extracted_text=data.get('extracted_text'),
            extracted_amount=data.get('extracted_amount'),
            extracted_date=data.get('extracted_date'),
            extracted_vendor=data.get('extracted_vendor'),
            extracted_category=data.get('extracted_category'),
            validation_status=data.get('validation_status', 'PENDING'),
            validation_rules=json.dumps(data.get('validation_rules', [])),
            normalized_amount=data.get('normalized_amount'),
            warnings=json.dumps(data.get('warnings', [])),
            errors=json.dumps(data.get('errors', []))
        )
        db.session.add(result)
        db.session.commit()
        return result

    def get_validation_result(self, receipt_id: int) -> Optional[ValidationResult]:
        return ValidationResult.query.filter_by(receipt_id=receipt_id).first()

    def update_validation_result(self, receipt_id: int, data: Dict) -> Optional[ValidationResult]:
        result = self.get_validation_result(receipt_id)
        if not result:
            return None

        for key, value in data.items():
            if hasattr(result, key):
                if key in ['validation_rules', 'warnings', 'errors'] and isinstance(value, list):
                    setattr(result, key, json.dumps(value))
                else:
                    setattr(result, key, value)

        result.updated_at = datetime.utcnow()
        db.session.commit()
        return result

    def retry_ocr(self, receipt_id: int) -> Optional[Receipt]:
        receipt = self.get_receipt(receipt_id)
        if not receipt:
            return None

        receipt.status = 'PENDING_OCR'
        receipt.updated_at = datetime.utcnow()
        db.session.commit()

        # Re-publish to OCR queue
        self._publish_to_ocr_queue(receipt)

        return receipt

    def _publish_to_ocr_queue(self, receipt: Receipt):
        """Publish to OCR queue for processing."""
        import os
        sqs = boto3.client('sqs', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        queue_url = os.getenv('OCR_QUEUE_URL')

        if not queue_url:
            logger.warning("OCR_QUEUE_URL not configured")
            return

        message = {
            'receipt_id': receipt.id,
            's3_object_key': receipt.s3_object_key,
            'report_id': receipt.report_id
        }

        try:
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
        except Exception as e:
            logger.error(f"Failed to publish to OCR queue: {e}")

    def _publish_event(self, event_type: str, data: Dict):
        """Publish event to message bus."""
        import os
        broker_url = os.getenv('MESSAGE_BUS_BROKER')

        if not broker_url:
            logger.warning("MESSAGE_BUS_BROKER not configured")
            return

        # TODO: Implement actual message bus (SNS, EventBridge, RabbitMQ, etc.)
        logger.info(f"Event published: {event_type} - {data}")


class ValidationService:
    """Handles validation result queries and analysis."""

    def get_receipt_validation(self, receipt_id: int) -> Optional[Dict]:
        result = ValidationResult.query.filter_by(receipt_id=receipt_id).first()
        if not result:
            return None

        return result.to_dict()

    def get_report_validation_summary(self, report_id: int) -> Dict:
        receipts = Receipt.query.filter_by(report_id=report_id).all()

        summary = {
            'total_receipts': len(receipts),
            'validated_receipts': 0,
            'passed_receipts': 0,
            'warning_receipts': 0,
            'failed_receipts': 0,
            'total_amount': 0,
            'warnings': [],
            'errors': []
        }

        for receipt in receipts:
            result = ValidationResult.query.filter_by(receipt_id=receipt.id).first()
            if result:
                summary['validated_receipts'] += 1

                if result.validation_status == 'PASS':
                    summary['passed_receipts'] += 1
                    if result.normalized_amount:
                        summary['total_amount'] += float(result.normalized_amount)
                elif result.validation_status == 'WARN':
                    summary['warning_receipts'] += 1
                    if result.warnings:
                        try:
                            warnings = json.loads(result.warnings)
                            summary['warnings'].extend(warnings)
                        except:
                            pass
                elif result.validation_status == 'FAIL':
                    summary['failed_receipts'] += 1
                    if result.errors:
                        try:
                            errors = json.loads(result.errors)
                            summary['errors'].extend(errors)
                        except:
                            pass

        return summary
