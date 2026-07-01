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
    container.attrs = {'Config': {'Image': 'portainer/portainer:latest'}}
    container.name = "some_random_name"
    assert engine._is_portainer(container) is True

def test_is_portainer_by_tag_ce(engine):
    container = MagicMock()
    container.attrs = {'Config': {'Image': 'portainer/portainer-ce:2.19.4'}}
    container.name = "some_random_name"
    assert engine._is_portainer(container) is True

def test_is_portainer_by_name(engine):
    container = MagicMock()
    # Mocking empty attrs
    container.attrs = {}
    container.name = "my_portainer_instance"
    assert engine._is_portainer(container) is True

def test_is_portainer_by_name_uppercase(engine):
    container = MagicMock()
    # Simulate missing/inaccessible image attrs — fallback to name check
    type(container).attrs = PropertyMock(side_effect=AttributeError)
    container.name = "PORTAINER"
    assert engine._is_portainer(container) is True

def test_is_not_portainer(engine):
    container = MagicMock()
    container.attrs = {'Config': {'Image': 'nginx:latest'}}
    container.name = "my_web_server"
    assert engine._is_portainer(container) is False

def test_is_portainer_exception_in_tags_but_name_matches(engine):
    container = MagicMock()
    # Raise an exception when accessing attrs
    type(container).attrs = PropertyMock(side_effect=AttributeError)
    container.name = "portainer-agent"
    assert engine._is_portainer(container) is True

def test_is_portainer_exception_in_tags_and_name_does_not_match(engine):
    container = MagicMock()
    # Raise an exception when accessing attrs
    type(container).attrs = PropertyMock(side_effect=AttributeError)
    container.name = "nginx"
    assert engine._is_portainer(container) is False

def test_group_containers_empty(engine):
    assert engine._group_containers([]) == {}

def test_group_containers_compose_project(engine):
    container1 = MagicMock()
    container1.labels = {"com.docker.compose.project": "project_a"}
    container2 = MagicMock()
    container2.labels = {"com.docker.compose.project": "project_a"}

    candidates = [container1, container2]
    groups = engine._group_containers(candidates)

    assert list(groups.keys()) == ["project_a"]
    assert groups["project_a"] == [container1, container2]

def test_group_containers_standalone(engine):
    container1 = MagicMock()
    container1.labels = {}
    container1.name = "standalone_1"

    container2 = MagicMock()
    container2.labels = {}
    container2.name = "standalone_2"

    candidates = [container1, container2]
    groups = engine._group_containers(candidates)

    assert set(groups.keys()) == {"standalone_1", "standalone_2"}
    assert groups["standalone_1"] == [container1]
    assert groups["standalone_2"] == [container2]

def test_group_containers_mixed(engine):
    container1 = MagicMock()
    container1.labels = {"com.docker.compose.project": "project_b"}

    container2 = MagicMock()
    container2.labels = {}
    container2.name = "standalone_3"

    candidates = [container1, container2]
    groups = engine._group_containers(candidates)

    assert set(groups.keys()) == {"project_b", "standalone_3"}
    assert groups["project_b"] == [container1]
    assert groups["standalone_3"] == [container2]
