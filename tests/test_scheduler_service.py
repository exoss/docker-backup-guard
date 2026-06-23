import unittest
from unittest.mock import patch
import sys
from unittest.mock import MagicMock
sys.modules['schedule'] = MagicMock()
sys.modules['docker'] = MagicMock()
from app.scheduler_service import _prepare_heartbeat_url, send_heartbeat

class TestSchedulerService(unittest.TestCase):
    def test_prepare_heartbeat_url(self):
        url = "http://kuma/api/push/123?ping="
        prepared = _prepare_heartbeat_url(url)
        self.assertIn("status=up", prepared)
        self.assertIn("msg=System+Idle+-+Waiting+for+Schedule", prepared)

    def test_prepare_heartbeat_url_non_kuma(self):
        url = "http://hc-ping.com/123"
        prepared = _prepare_heartbeat_url(url)
        self.assertEqual(url, prepared)

    @patch('app.scheduler_service.requests.get')
    def test_send_heartbeat(self, mock_get):
        send_heartbeat("http://kuma/api/push/123?status=up")
        mock_get.assert_called_with("http://kuma/api/push/123?status=up", timeout=10)

if __name__ == "__main__":
    unittest.main()
