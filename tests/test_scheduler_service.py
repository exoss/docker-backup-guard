import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies that are not available in the test environment
sys.modules['docker'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['urllib3'] = MagicMock()
sys.modules['streamlit'] = MagicMock()
sys.modules['schedule'] = MagicMock()

from app.scheduler_service import _prepare_heartbeat_url, send_heartbeat, scheduler_loop
import requests

class TestSchedulerService(unittest.TestCase):
    def test_prepare_heartbeat_url_uptime_kuma(self):
        url = "http://kuma.local/api/push/TOKEN?status=up&msg=OK&ping="
        result = _prepare_heartbeat_url(url)
        self.assertIn("status=up", result)
        self.assertIn("msg=System+Idle+-+Waiting+for+Schedule", result)
        self.assertNotIn("msg=OK", result)

    def test_prepare_heartbeat_url_normal(self):
        url = "https://healthchecks.io/ping/12345"
        result = _prepare_heartbeat_url(url)
        self.assertEqual(result, url)

    @patch('app.scheduler_service.requests.get')
    def test_send_heartbeat(self, mock_get):
        send_heartbeat("http://example.com/ping")
        mock_get.assert_called_once_with("http://example.com/ping", timeout=10)

    @patch('app.scheduler_service.requests.get')
    def test_send_heartbeat_ssl_error(self, mock_get):
        class MockSSLError(Exception): pass
        import app.scheduler_service
        app.scheduler_service.requests.exceptions.SSLError = MockSSLError
        mock_get.side_effect = [MockSSLError("Mock SSL Error"), None]
        send_heartbeat("https://example.com/ping")
        self.assertEqual(mock_get.call_count, 2)
        mock_get.assert_called_with("https://example.com/ping", timeout=10, verify=False)

    @patch('app.scheduler_service.time.sleep')
    @patch('app.scheduler_service.os.stat')
    def test_scheduler_loop(self, mock_stat, mock_sleep):
        mock_stat.return_value.st_mtime = 12345
        mock_sleep.side_effect = [None, BaseException('Break Loop')]

        with self.assertRaises(BaseException) as context:
            scheduler_loop()

        self.assertEqual(str(context.exception), "Break Loop")

if __name__ == '__main__':
    unittest.main()
