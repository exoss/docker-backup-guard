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


    def test_encrypt_decrypt_valid_value(self):
        # Test full encryption and decryption cycle
        original_value = "secret_password_123!"
        encrypted = app.security.encrypt_value(original_value)

        self.assertTrue(encrypted.startswith("ENC("))
        self.assertTrue(encrypted.endswith(")"))
        self.assertNotEqual(original_value, encrypted)

        decrypted = app.security.decrypt_value(encrypted)
        self.assertEqual(original_value, decrypted)

    def test_encrypt_empty_value(self):
        self.assertEqual(app.security.encrypt_value(""), "")
        self.assertEqual(app.security.encrypt_value(None), "")

    def test_decrypt_empty_value(self):
        self.assertEqual(app.security.decrypt_value(""), "")
        self.assertEqual(app.security.decrypt_value(None), "")

    def test_encrypt_already_encrypted_value(self):
        encrypted = "ENC(already_encrypted_token)"
        result = app.security.encrypt_value(encrypted)
        self.assertEqual(result, encrypted)

    def test_decrypt_unencrypted_value(self):
        unencrypted = "not_encrypted_string"
        result = app.security.decrypt_value(unencrypted)
        self.assertEqual(result, unencrypted)

    def test_decrypt_invalid_encrypted_format(self):
        # Test decryption with invalid token format inside ENC()
        invalid_encrypted = "ENC(invalid_token)"
        # Fernet decrypt will fail, should return the original string
        result = app.security.decrypt_value(invalid_encrypted)
        self.assertEqual(result, invalid_encrypted)

    def test_encrypt_key_error(self):
        # Force a key error to test exception handling in encrypt
        with patch('app.security._get_key', side_effect=Exception("Mocked key error")):
            result = app.security.encrypt_value("test_val")
            self.assertEqual(result, "test_val")

if __name__ == '__main__':
    unittest.main()
