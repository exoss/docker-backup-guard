import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies that are not available in the test environment
for mod in ['docker', 'dotenv', 'requests', 'urllib3', 'schedule', 'streamlit']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from app.scheduler_service import _prepare_heartbeat_url, send_heartbeat

class TestSchedulerService(unittest.TestCase):
    def test_prepare_heartbeat_url_empty(self):
        self.assertEqual(_prepare_heartbeat_url(""), "")
        self.assertEqual(_prepare_heartbeat_url(None), "")

    def test_prepare_heartbeat_url_non_push(self):
        url = "http://example.com/api/status"
        self.assertEqual(_prepare_heartbeat_url(url), url)

    def test_prepare_heartbeat_url_push_valid(self):
        url = "http://uptime.kuma/api/push/xyz"
        expected_url = "http://uptime.kuma/api/push/xyz?status=up&msg=System+Idle+-+Waiting+for+Schedule"
        self.assertEqual(_prepare_heartbeat_url(url), expected_url)

    def test_prepare_heartbeat_url_push_with_existing_query(self):
        url = "http://uptime.kuma/api/push/xyz?foo=bar"
        expected_url = "http://uptime.kuma/api/push/xyz?foo=bar&status=up&msg=System+Idle+-+Waiting+for+Schedule"
        self.assertEqual(_prepare_heartbeat_url(url), expected_url)

    @patch('urllib.parse.urlparse', side_effect=Exception("Mocked parse exception"))
    def test_prepare_heartbeat_url_exception(self, _mock_parse):
        url = "http://uptime.kuma/api/push/xyz"
        self.assertEqual(_prepare_heartbeat_url(url), url)

    @patch('app.scheduler_service.logger.warning')
    @patch('app.scheduler_service._heartbeat_session.get')
    def test_send_heartbeat_success(self, mock_get, mock_warning):
        response = MagicMock()
        response.status_code = 200
        mock_get.return_value = response

        send_heartbeat("http://example.com/heartbeat")

        mock_get.assert_called_once_with("http://example.com/heartbeat", timeout=10, verify=False)
        response.raise_for_status.assert_called_once()
        self.assertFalse(mock_warning.called)

    @patch('app.scheduler_service.logger.warning')
    @patch('app.scheduler_service._heartbeat_session.get')
    def test_send_heartbeat_http_error_logs_warning(self, mock_get, mock_warning):
        response = MagicMock()
        response.raise_for_status.side_effect = Exception("404 Client Error")
        mock_get.return_value = response

        send_heartbeat("http://example.com/missing")

        mock_get.assert_called_once_with("http://example.com/missing", timeout=10, verify=False)
        mock_warning.assert_called_once()
        self.assertIn("Heartbeat failed: 404 Client Error", mock_warning.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
