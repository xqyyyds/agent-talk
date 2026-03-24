import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


THIS_FILE = Path(__file__).resolve()
ADMIN_BACKEND_ROOT = THIS_FILE.parents[3] / "admin" / "backend"
if not ADMIN_BACKEND_ROOT.exists():
    ADMIN_BACKEND_ROOT = THIS_FILE.parents[1]
sys.path.insert(0, str(ADMIN_BACKEND_ROOT))

from app.deps import get_current_admin  # noqa: E402
from app.routers import uploads  # noqa: E402


class AdminAvatarUploadRouterTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(uploads.router)
        app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(id=1)
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.clear)

    def test_upload_avatar_proxies_file_and_returns_avatar_path(self):
        response_payload = Mock()
        response_payload.raise_for_status.return_value = None
        response_payload.json.return_value = {
            "code": 200,
            "data": {"avatar": "/api/uploads/avatars/2026/03/sample.png"},
        }

        with patch("app.routers.uploads.httpx.post", return_value=response_payload) as post:
            res = self.client.post(
                "/admin/uploads/avatar",
                files={"file": ("avatar.png", io.BytesIO(b"png-bytes"), "image/png")},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(200, res.status_code)
        self.assertEqual(
            "/api/uploads/avatars/2026/03/sample.png",
            res.json()["data"]["avatar"],
        )
        self.assertTrue(post.called)

    def test_upload_avatar_returns_502_when_backend_upload_fails(self):
        with patch("app.routers.uploads.httpx.post", side_effect=RuntimeError("boom")):
            res = self.client.post(
                "/admin/uploads/avatar",
                files={"file": ("avatar.png", io.BytesIO(b"png-bytes"), "image/png")},
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(502, res.status_code)
        self.assertEqual("头像上传失败", res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
