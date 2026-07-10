import unittest
from unittest.mock import patch, MagicMock

# We need to mock dependencies that might not be installed in the test environment,
# but we MUST NOT do it globally in sys.modules, otherwise we pollute the environment.
# Instead, we will patch them where they are used.

class TestAPIHandlers(unittest.TestCase):
    @patch('app.api_handlers.requests.Session')
    @patch.dict('os.environ', {'GOTIFY_URL': 'http://gotify.example.com', 'GOTIFY_TOKEN': 'enc_token'})
    @patch('app.api_handlers.decrypt_value', return_value='test_token')
    def test_send_gotify_notification_secure_headers(self, _mock_decrypt, mock_session_class):
        # Local mock of the Session instance
        mock_session_instance = MagicMock()
        mock_session_class.return_value = mock_session_instance

        # Import inside the test to allow patch to work
        from app.api_handlers import APIHandler
        handler = APIHandler()

        handler.send_gotify_notification("Test", "Message")

        mock_session_instance.post.assert_called_once()
        args, kwargs = mock_session_instance.post.call_args

        # Verify URL doesn't contain token
        self.assertEqual(args[0], "http://gotify.example.com/message")

        # Verify header contains token
        self.assertIn("headers", kwargs)
        self.assertEqual(kwargs["headers"]["X-Gotify-Key"], "test_token")

    @patch('app.api_handlers.requests.post')
    def test_gotify_connection_secure_headers(self, mock_post):
        from app.api_handlers import APIHandler
        APIHandler.test_gotify_connection('http://gotify.example.com', 'test_token')

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        # Verify URL doesn't contain token
        self.assertEqual(args[0], "http://gotify.example.com/message")

        # Verify header contains token
        self.assertIn("headers", kwargs)
        self.assertEqual(kwargs["headers"]["X-Gotify-Key"], "test_token")

    @patch('app.api_handlers.get_env_bool', return_value=True)
    @patch('app.api_handlers.requests.get')
    def test_portainer_connection_respects_verify_ssl(self, mock_get, _mock_get_env_bool):
        from app.api_handlers import APIHandler

        response = MagicMock()
        response.json.return_value = [{"Id": 1}]
        mock_get.return_value = response

        result = APIHandler.test_portainer_connection('https://portainer.example.com', 'test_token')

        self.assertEqual(result, [{"Id": 1}])
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        self.assertTrue(kwargs["verify"])
