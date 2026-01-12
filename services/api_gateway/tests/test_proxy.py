import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch
from api_gateway.proxy import ServiceProxy


class TestServiceProxy:
    """Test ServiceProxy."""

    @pytest.fixture
    def proxy(self):
        """Create ServiceProxy instance."""
        return ServiceProxy()

    def test_forward_request_success(self, proxy):
        """Test successful request forwarding."""
        with patch('api_gateway.proxy.request') as mock_request:
            # Mock Flask request object
            mock_request.method = 'GET'
            mock_request.headers = {'Authorization': 'Bearer token'}
            mock_request.args = {}
            mock_request.remote_addr = '127.0.0.1'
            mock_request.url = 'http://localhost:8080/v1/reports'
            mock_request.is_json = False

            with patch('api_gateway.proxy.service_discovery') as mock_discovery:
                mock_discovery.get_service_url.return_value = 'http://mock-service:5000'
                mock_discovery.check_health.return_value = True

                with patch('api_gateway.proxy.ServiceProxy.session.request') as mock_session:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'id': 1, 'title': 'Test Report'}
                    mock_response.headers = {'content-type': 'application/json'}
                    mock_session.return_value = mock_response

                    data, status, headers = proxy.forward_request('reports', '/v1/reports')

                    assert status == 200
                    assert data['id'] == 1
                    assert data['title'] == 'Test Report'

    def test_forward_request_service_unavailable(self, proxy):
        """Test forwarding to unhealthy service."""
        with patch('api_gateway.proxy.service_discovery') as mock_discovery:
            mock_discovery.get_service_url.return_value = 'http://mock-service:5000'
            mock_discovery.check_health.return_value = False

            data, status, headers = proxy.forward_request('reports', '/v1/reports')

            assert status == 503
            assert 'Service reports is unavailable' in data['error']

    def test_forward_request_timeout(self, proxy):
        """Test request timeout."""
        with patch('api_gateway.proxy.request') as mock_request:
            mock_request.method = 'GET'
            mock_request.headers = {}
            mock_request.args = {}
            mock_request.remote_addr = '127.0.0.1'
            mock_request.url = 'http://localhost:8080/v1/reports'
            mock_request.is_json = False

            with patch('api_gateway.proxy.service_discovery') as mock_discovery:
                mock_discovery.get_service_url.return_value = 'http://mock-service:5000'
                mock_discovery.check_health.return_value = True

                with patch('api_gateway.proxy.ServiceProxy.session.request') as mock_session:
                    from requests.exceptions import Timeout
                    mock_session.side_effect = Timeout('Request timed out')

                    data, status, headers = proxy.forward_request('reports', '/v1/reports')

                    assert status == 504
                    assert 'Service timeout' in data['error']
