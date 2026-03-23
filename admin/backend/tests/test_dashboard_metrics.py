import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "admin" / "backend"))

from app.routers import dashboard  # noqa: E402


class _ScalarQuery:
    def __init__(self, value):
        self._value = value

    def filter(self, *args, **kwargs):
        return self

    def count(self):
        return self._value

    def scalar(self):
        return self._value


class _OverviewDB:
    def query(self, *entities):
        entity_names = {getattr(entity, "__name__", str(entity)) for entity in entities}
        if "UserLoginEvent" in entity_names and len(entities) == 1:
            return _ScalarQuery(7)
        return _ScalarQuery(0)


class DashboardMetricsTests(unittest.TestCase):
    def test_dashboard_overview_uses_presence_for_active_users_24h(self):
        db = _OverviewDB()
        with (
            patch.object(dashboard, "_online_users_5m", return_value=2),
            patch.object(dashboard, "_active_users_24h", return_value=3),
        ):
            payload = dashboard.dashboard_overview(db=db, _=SimpleNamespace())

        self.assertEqual(2, payload["online_users_5m"])
        self.assertEqual(3, payload["active_users_24h"])
        self.assertEqual(7, payload["login_events_24h"])


if __name__ == "__main__":
    unittest.main()
