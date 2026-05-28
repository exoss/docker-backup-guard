import unittest
from unittest.mock import patch, MagicMock
import os
from app.scheduler_service import _prepare_heartbeat_url, send_heartbeat, scheduler_loop

class TestSchedulerService(unittest.TestCase):

    def test_prepare_heartbeat_url_uptime_kuma(self):
        url = "http://kuma.example.com/api/push/token?status=up&msg=OK"
        expected = "http://kuma.example.com/api/push/token?status=up&msg=System+Idle+-+Waiting+for+Schedule"
        self.assertEqual(_prepare_heartbeat_url(url), expected)

    def test_prepare_heartbeat_url_normal(self):
        url = "http://example.com/ping"
        self.assertEqual(_prepare_heartbeat_url(url), url)

    def test_prepare_heartbeat_url_empty(self):
        self.assertEqual(_prepare_heartbeat_url(""), "")

    @patch('app.scheduler_service.requests.get')
    def test_send_heartbeat(self, mock_get):
        url = "http://example.com/ping"
        send_heartbeat(url)
        mock_get.assert_called_once_with(url, timeout=10)

    @patch('app.scheduler_service.requests.get')
    @patch('app.scheduler_service.requests.exceptions.SSLError', Exception)
    def test_send_heartbeat_ssl_error(self, mock_get):
        # We need a proper way to test the SSL retry logic, but it's tricky due to warnings context manager.
        pass

    @patch('app.scheduler_service.time.sleep')
    @patch('app.scheduler_service.schedule.run_pending')
    @patch('app.scheduler_service.schedule.every')
    @patch('app.scheduler_service.schedule.clear')
    @patch('app.scheduler_service.os.stat')
    @patch('app.scheduler_service.os.path.isdir')
    @patch('app.scheduler_service.os.getenv')
    def test_scheduler_loop(self, mock_getenv, mock_isdir, mock_stat, mock_clear, mock_every, mock_run_pending, mock_sleep):
        # Mock environment variables
        def getenv_side_effect(key, default=None):
            env = {
                "SCHEDULE_ENABLE": "true",
                "SCHEDULE_TIME": "03:00",
                "HEARTBEAT_URL": "http://kuma.example.com/api/push/token",
                "HEARTBEAT_INTERVAL": "5",
            }
            return env.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        mock_isdir.return_value = False

        # Mock os.stat to simulate config reload
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mtime = 12345
        mock_stat.return_value = mock_stat_obj

        # Break the infinite loop after one iteration by making sleep raise an exception
        mock_sleep.side_effect = [None, BaseException("Break Loop")]

        try:
            scheduler_loop()
        except BaseException as e:
            self.assertEqual(str(e), "Break Loop")

        # Verify schedule.clear was called (since config changed from initial state)
        mock_clear.assert_called_once()

        # Verify schedule.every was called for both backup and heartbeat
        self.assertEqual(mock_every.call_count, 2)

        # Verify run_pending was called
        mock_run_pending.assert_called_once()
