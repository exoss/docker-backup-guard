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


    def test_encrypt_value_empty(self):
        self.assertEqual(app.security.encrypt_value(""), "")
        self.assertEqual(app.security.encrypt_value(None), "")

    def test_encrypt_value_already_encrypted(self):
        self.assertEqual(app.security.encrypt_value("ENC(something)"), "ENC(something)")

    @patch('app.security._get_key')
    def test_encrypt_value_success(self, mock_get_key):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        mock_get_key.return_value = key

        result = app.security.encrypt_value("my_secret")
        self.assertTrue(result.startswith("ENC("))
        self.assertTrue(result.endswith(")"))

        # Verify it can be decrypted
        token = result[4:-1]
        f = Fernet(key)
        decrypted = f.decrypt(token.encode()).decode()
        self.assertEqual(decrypted, "my_secret")

    @patch('app.security._get_key')
    def test_encrypt_value_exception(self, mock_get_key):
        mock_get_key.side_effect = Exception("Mocked exception")
        # Should return original value on error
        self.assertEqual(app.security.encrypt_value("my_secret"), "my_secret")

if __name__ == '__main__':
    unittest.main()
