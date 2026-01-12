import os
import requests
from typing import Dict, Optional, List
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class ServiceDiscovery:
    """Service discovery for locating microservices."""

    def __init__(self):
        self.services = {
            'reports': os.getenv('REPORT_SERVICE_URL', 'http://report-service:5000'),
            'receipts': os.getenv('RECEIPT_SERVICE_URL', 'http://receipt-service:5001'),
            'review': os.getenv('REVIEW_SERVICE_URL', 'http://review-service:5002'),
        }
        self.health_status = {name: True for name in self.services}

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the URL for a service."""
        return self.services.get(service_name)

    def check_health(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        url = self.services.get(service_name)
        if not url:
            return False

        try:
            response = requests.get(f"{url}/health", timeout=2)
            healthy = response.status_code == 200
            self.health_status[service_name] = healthy
            return healthy
        except Exception as e:
            logger.warning(f"Service {service_name} health check failed: {e}")
            self.health_status[service_name] = False
            return False

    def get_all_health(self) -> Dict[str, bool]:
        """Get health status of all services."""
        health = {}
        for service_name in self.services:
            health[service_name] = self.check_health(service_name)
        return health

# Global service discovery instance
service_discovery = ServiceDiscovery()

def get_service_url(service_name: str) -> str:
    """Get service URL or raise error if not configured."""
    url = service_discovery.get_service_url(service_name)
    if not url:
        raise ValueError(f"Service URL not configured: {service_name}")
    return url
