import sys
from unittest.mock import MagicMock

# Mock required modules before importing app.engine
sys.modules['docker'] = MagicMock()
sys.modules['dotenv'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['urllib3'] = MagicMock()
sys.modules['schedule'] = MagicMock()
sys.modules['streamlit'] = MagicMock()

import unittest
from app.engine import BackupEngine

class MockContainer:
    def __init__(self, name, labels=None):
        self.name = name
        self.labels = labels or {}

class TestBackupEngineGroupContainers(unittest.TestCase):
    def setUp(self):
        # Create an instance without calling __init__ to avoid side effects
        self.engine = BackupEngine.__new__(BackupEngine)

    def test_group_containers_empty(self):
        """Test with an empty list of candidates."""
        result = self.engine._group_containers([])
        self.assertEqual(result, {})

    def test_group_containers_with_projects(self):
        """Test grouping containers that share the same compose project label."""
        c1 = MockContainer("db", {"com.docker.compose.project": "app_stack"})
        c2 = MockContainer("web", {"com.docker.compose.project": "app_stack"})
        c3 = MockContainer("redis", {"com.docker.compose.project": "cache_stack"})

        candidates = [c1, c2, c3]
        result = self.engine._group_containers(candidates)

        self.assertEqual(len(result), 2)
        self.assertIn("app_stack", result)
        self.assertIn("cache_stack", result)
        self.assertEqual(result["app_stack"], [c1, c2])
        self.assertEqual(result["cache_stack"], [c3])

    def test_group_containers_standalone(self):
        """Test grouping containers without compose project labels."""
        c1 = MockContainer("nginx_standalone", {})
        c2 = MockContainer("mysql_standalone", {"other_label": "value"})

        candidates = [c1, c2]
        result = self.engine._group_containers(candidates)

        self.assertEqual(len(result), 2)
        self.assertIn("nginx_standalone", result)
        self.assertIn("mysql_standalone", result)
        self.assertEqual(result["nginx_standalone"], [c1])
        self.assertEqual(result["mysql_standalone"], [c2])

    def test_group_containers_mixed(self):
        """Test a mix of compose project and standalone containers."""
        c1 = MockContainer("db", {"com.docker.compose.project": "app_stack"})
        c2 = MockContainer("standalone", {})
        c3 = MockContainer("web", {"com.docker.compose.project": "app_stack"})

        candidates = [c1, c2, c3]
        result = self.engine._group_containers(candidates)

        self.assertEqual(len(result), 2)
        self.assertIn("app_stack", result)
        self.assertIn("standalone", result)
        self.assertEqual(result["app_stack"], [c1, c3])
        self.assertEqual(result["standalone"], [c2])

if __name__ == '__main__':
    unittest.main()
