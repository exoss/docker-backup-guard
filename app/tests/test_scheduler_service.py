import sys
from unittest.mock import MagicMock, patch

# Mock missing modules just for this test file context
for mod in ['docker', 'dotenv', 'requests', 'urllib3', 'schedule', 'streamlit']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from app.scheduler_service import _prepare_heartbeat_url, send_heartbeat

def test_prepare_heartbeat_url_empty():
    assert _prepare_heartbeat_url("") == ""
    assert _prepare_heartbeat_url(None) == ""

def test_prepare_heartbeat_url_no_api_push():
    url = "https://example.com/health"
    assert _prepare_heartbeat_url(url) == url

def test_prepare_heartbeat_url_with_api_push_no_query():
    url = "https://kuma.example.com/api/push/12345"
    expected = "https://kuma.example.com/api/push/12345?status=up&msg=System+Idle+-+Waiting+for+Schedule"
    assert _prepare_heartbeat_url(url) == expected

def test_prepare_heartbeat_url_with_api_push_existing_query():
    url = "https://kuma.example.com/api/push/12345?foo=bar&status=down"
    import urllib.parse
    result = _prepare_heartbeat_url(url)
    parsed = urllib.parse.urlparse(result)
    query = urllib.parse.parse_qs(parsed.query)

    assert "https://kuma.example.com/api/push/12345" == f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    assert query['foo'] == ['bar']
    assert query['status'] == ['up']
    assert query['msg'] == ['System Idle - Waiting for Schedule']

def test_prepare_heartbeat_url_exception_fallback():
    with patch('urllib.parse.urlparse', side_effect=Exception("Parsing error")):
        url = "https://kuma.example.com/api/push/12345"
        assert _prepare_heartbeat_url(url) == url

@patch('app.scheduler_service.requests.get')
def test_send_heartbeat_success(mock_get):
    url = "https://example.com/heartbeat"
    send_heartbeat(url)
    mock_get.assert_called_once_with(url, timeout=10, verify=False)

@patch('app.scheduler_service.logger.warning')
@patch('app.scheduler_service.requests.get')
def test_send_heartbeat_exception(mock_get, mock_warning):
    mock_get.side_effect = Exception("Connection error")
    url = "https://example.com/heartbeat"
    send_heartbeat(url)
    mock_get.assert_called_once_with(url, timeout=10, verify=False)
    mock_warning.assert_called_once_with("Heartbeat failed: Connection error")
