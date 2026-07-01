import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies that are not available in the test environment
for mod in ['docker', 'dotenv', 'requests', 'urllib3', 'schedule', 'streamlit']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from app.scheduler_service import _prepare_heartbeat_url

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
    def test_prepare_heartbeat_url_exception(self, mock_parse):
        url = "http://uptime.kuma/api/push/xyz"
        self.assertEqual(_prepare_heartbeat_url(url), url)

if __name__ == '__main__':
    unittest.main()
