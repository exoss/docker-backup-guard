import sys
import unittest
from unittest.mock import MagicMock, patch


streamlit_stub = MagicMock()
streamlit_stub.cache_data = lambda func: func
streamlit_stub.session_state = {}

sys.modules.setdefault("streamlit", streamlit_stub)
sys.modules.setdefault("docker", MagicMock())

from app import ui


class TestUI(unittest.TestCase):
    def setUp(self):
        ui.st.session_state = {}

    @patch("app.ui.show_dashboard")
    @patch("app.ui.check_password")
    @patch("app.ui.show_setup_wizard")
    @patch("app.ui.load_env_cached")
    @patch("app.ui.decrypt_value")
    @patch("app.ui.os.getenv")
    def test_run_missing_web_ui_credentials_shows_setup(
        self,
        mock_getenv,
        mock_decrypt,
        mock_load_env,
        mock_show_setup,
        mock_check_password,
        mock_show_dashboard,
    ):
        def getenv_side_effect(key, default=None):
            values = {
                "BACKUP_PASSWORD": "ENC(backup)",
                "WEB_UI_USERNAME": "",
                "WEB_UI_PASSWORD": "",
            }
            return values.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        mock_decrypt.return_value = ""

        ui.run()

        mock_load_env.assert_called_once_with()
        mock_show_setup.assert_called_once_with()
        mock_check_password.assert_not_called()
        mock_show_dashboard.assert_not_called()


if __name__ == "__main__":
    unittest.main()
