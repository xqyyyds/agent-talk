import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent_service"))

from app.core import crawler_jobs, runtime_config  # noqa: E402


class _DummyRedis:
    def __init__(self) -> None:
        self.set_calls: list[dict[str, object]] = []

    async def set(self, key, value, nx=None, ex=None):
        self.set_calls.append({"key": key, "value": value, "nx": nx, "ex": ex})
        return True

    async def hset(self, key, mapping):
        return 1

    async def expire(self, key, seconds):
        return True

    async def lpush(self, key, value):
        return 1

    async def ltrim(self, key, start, end):
        return True

    async def aclose(self):
        return None


class TestCrawlerRuntimeTimeout(unittest.TestCase):
    def test_runtime_config_normalizes_crawler_timeout(self) -> None:
        self.assertEqual(
            300,
            runtime_config._normalize_value("crawler_job_timeout_seconds", "120"),
        )
        self.assertEqual(
            900,
            runtime_config._normalize_value("crawler_job_timeout_seconds", "900"),
        )

    def test_create_job_uses_runtime_timeout_seconds(self) -> None:
        manager = crawler_jobs.CrawlerJobManager()
        dummy_redis = _DummyRedis()

        async def fake_run_job(*args, **kwargs):
            return None

        def fake_create_task(coro):
            coro.close()
            return object()

        with (
            patch.object(
                manager,
                "_redis",
                AsyncMock(return_value=dummy_redis),
            ),
            patch.object(
                manager,
                "_reconcile_stale_jobs",
                AsyncMock(return_value=None),
            ),
            patch.object(
                manager,
                "_resolve_job_timeout_seconds",
                AsyncMock(return_value=1200),
            ),
            patch.object(manager, "_run_job", AsyncMock(side_effect=fake_run_job)) as mocked_run,
            patch("app.core.crawler_jobs.asyncio.create_task", side_effect=fake_create_task),
        ):
            job = asyncio.run(manager.create_job("zhihu"))

        self.assertEqual(1200, job["timeout_seconds"])
        mocked_run.assert_called_once()
        args = mocked_run.call_args.args
        self.assertEqual(job["job_id"], args[0])
        self.assertEqual("zhihu", args[1])
        self.assertEqual("zhihu_hotspot_crawler.py", args[2])
        self.assertEqual(1200, args[4])


if __name__ == "__main__":
    unittest.main()
