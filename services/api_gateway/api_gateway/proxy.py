import requests  # type: ignore
import logging
from flask import request, g
from .service_discovery import get_service_url, service_discovery

logger = logging.getLogger(__name__)


class ServiceProxy:
    """Proxy requests to backend microservices."""

    def __init__(self):
        self.session = requests.Session()

    def forward_request(self, service_name: str, path: str, timeout: int = 30) -> tuple:
        """
        Forward the current request to a backend service.

        Args:
            service_name: Name of the service (reports, receipts, review)
            path: Path to forward to
            timeout: Request timeout in seconds

        Returns:
            Tuple of (response_data, status_code, headers)
        """
        try:
            # Get service URL
            base_url = get_service_url(service_name)

            # Check health
            if not service_discovery.check_health(service_name):
                return {"error": f"Service {service_name} is unavailable"}, 503, {}

            # Build target URL
            target_url = f"{base_url}{path}"

            # Get request data
            method = request.method
            headers = {
                k: v
                for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length"]
            }

            # Add forwarded information
            headers["X-Forwarded-For"] = request.remote_addr
            headers["X-Original-URI"] = request.url

            # For development, add authentication info if available
            if hasattr(g, "user"):
                headers["X-User-ID"] = g.user.get("user_id", "")
                headers["X-User-Role"] = g.user.get("role", "")
                headers["X-User-Email"] = g.user.get("user_email", "")

            # Forward request
            data = None
            if method in ["POST", "PUT", "PATCH"]:
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.get_data()

            logger.info(f"Forwarding {method} {target_url}")

            response = self.session.request(
                method=method,
                url=target_url,
                headers=headers,
                json=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None,
                params=request.args,
                timeout=timeout,
            )

            # Return response
            try:
                response_data = response.json()
            except Exception:
                response_data = response.text

            # Filter headers to forward
            forward_headers = {}
            for key in ["content-type", "location", "etag"]:
                if key in response.headers:
                    forward_headers[key] = response.headers[key]

            return response_data, response.status_code, forward_headers

        except requests.exceptions.Timeout:
            logger.error(f"Timeout forwarding to {service_name}")
            return {"error": "Service timeout"}, 504, {}
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {service_name}")
            return {"error": f"Cannot connect to service {service_name}"}, 503, {}
        except Exception as e:
            logger.error(f"Error forwarding to {service_name}: {e}")
            return {"error": f"Proxy error: {str(e)}"}, 500, {}
