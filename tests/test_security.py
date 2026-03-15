import os
import unittest
from unittest.mock import patch, mock_open
import tempfile
import importlib

# To test this, we should patch app.security.KEY_FILE or patch os.path.exists
import app.security

class TestSecurity(unittest.TestCase):
    def setUp(self):
        # Clear lru_cache for _get_key
        app.security._get_key.cache_clear()

    def test_get_key_file_unreadable_raises_exception(self):
        with patch('os.path.exists', return_value=True):
            # Mock open to raise an exception (e.g., PermissionError)
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                with self.assertRaises(RuntimeError) as context:
                    app.security._get_key()

                self.assertIn("Failed to read existing encryption key: Permission denied", str(context.exception))

    def test_get_key_file_readable(self):
        mock_key = b'mocked_key_bytes'
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_key)):
                key = app.security._get_key()
                self.assertEqual(key, mock_key)

    def test_get_key_file_not_exists_generates_new(self):
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open()) as mock_file:
                with patch('os.makedirs') as mock_makedirs:
                    key = app.security._get_key()
                    self.assertIsNotNone(key)
                    self.assertEqual(len(key), 44) # Fernet key is 44 bytes base64
                    mock_makedirs.assert_called_once()
                    mock_file.assert_called_once()

if __name__ == '__main__':
    unittest.main()
