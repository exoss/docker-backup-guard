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

from app.engine import BackupEngine

class TestBackupEngine(unittest.TestCase):
    def setUp(self):
        # We use __new__ to avoid calling __init__ which might try to connect to Docker or read files
        self.engine = BackupEngine.__new__(BackupEngine)
        self.engine._log = MagicMock()

    @patch('time.sleep', return_value=None)
    def test_retry_operation_success_first_try(self, mock_sleep):
        mock_func = MagicMock(return_value="success")

        result = self.engine._retry_operation(mock_func, retries=3, delay=5)

        self.assertEqual(result, "success")
        mock_func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch('time.sleep', return_value=None)
    def test_retry_operation_success_after_retries(self, mock_sleep):
        # Fails first two times, succeeds on third
        mock_func = MagicMock(side_effect=[ValueError("fail 1"), ValueError("fail 2"), "success"])

        result = self.engine._retry_operation(mock_func, retries=3, delay=5)

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(5)

    @patch('time.sleep', return_value=None)
    def test_retry_operation_failure(self, mock_sleep):
        # Always fails
        mock_func = MagicMock(side_effect=ValueError("always fail"))

        with self.assertRaises(ValueError) as context:
            self.engine._retry_operation(mock_func, retries=3, delay=5)

        self.assertEqual(str(context.exception), "always fail")
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_called_with(5)

    @patch('app.engine.subprocess.run')
    def test_run_encrypted_7z_uses_stdin_for_password(self, mock_run):
        self.engine.backup_password = "super-secret"

        self.engine._run_encrypted_7z(
            "/backups/archive.7z",
            ".",
            cwd="/tmp/source",
            extra_args=["-mmt=2"],
            timeout=1800,
        )

        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        cmd = kwargs["args"] if "args" in kwargs else mock_run.call_args[0][0]
        self.assertIn("-p", cmd)
        self.assertNotIn("super-secret", " ".join(cmd))
        self.assertEqual(kwargs["cwd"], "/tmp/source")
        self.assertEqual(kwargs["timeout"], 1800)
        self.assertEqual(kwargs["input"], "super-secret\nsuper-secret\n")
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])

if __name__ == '__main__':
    unittest.main()
