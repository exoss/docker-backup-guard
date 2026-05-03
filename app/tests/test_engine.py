import sys
from unittest.mock import MagicMock, patch, PropertyMock

# Mock missing modules just for this test file context
import pytest

# We only mock these if they are not already imported to avoid breaking other tests
# This is a workaround for the current environment missing dependencies
for mod in ['docker', 'dotenv', 'requests', 'urllib3', 'schedule', 'streamlit']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from app.engine import BackupEngine

@pytest.fixture
def engine():
    with patch('os.makedirs'):
        return BackupEngine()

def test_is_portainer_by_tag(engine):
    container = MagicMock()
    container.attrs = {"Config": {"Image": "portainer/portainer:latest"}}
    container.name = "some_random_name"
    assert engine._is_portainer(container) is True

def test_is_portainer_by_tag_ce(engine):
    container = MagicMock()
    container.attrs = {"Config": {"Image": "portainer/portainer-ce:2.19.4"}}
    container.name = "some_random_name"
    assert engine._is_portainer(container) is True

def test_is_portainer_by_name(engine):
    container = MagicMock()
    # Mocking empty tags or exception
    container.attrs = {}
    container.name = "my_portainer_instance"
    assert engine._is_portainer(container) is True

def test_is_portainer_by_name_uppercase(engine):
    container = MagicMock()
    container.attrs = {}
    container.name = "PORTAINER"
    assert engine._is_portainer(container) is True

def test_is_not_portainer(engine):
    container = MagicMock()
    container.attrs = {"Config": {"Image": "nginx:latest"}}
    container.name = "my_web_server"
    assert engine._is_portainer(container) is False

def test_is_portainer_exception_in_tags_but_name_matches(engine):
    container = MagicMock()
    # Raise an exception when accessing tags
    type(container).attrs = PropertyMock(side_effect=AttributeError)
    container.name = "portainer-agent"
    assert engine._is_portainer(container) is True

def test_is_portainer_exception_in_tags_and_name_does_not_match(engine):
    container = MagicMock()
    # Raise an exception when accessing tags
    type(container).attrs = PropertyMock(side_effect=AttributeError)
    container.name = "nginx"
    assert engine._is_portainer(container) is False
