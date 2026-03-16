"""
Go 后端 API 客户端

简化版：去除冗余逻辑，保持核心功能
"""

import httpx
from typing import List, Dict
from app.config import settings


class BackendAPIClient:
    """Go 后端 API 客户端"""

    def __init__(self):
        self.base_url = settings.backend_url
        self.timeout = 30.0

    async def _request(self, method: str, path: str, **kwargs) -> Dict:
        """统一的请求方法"""
        url = f"{self.base_url}{path}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
            data = response.json()

            if data.get("code") == 200:
                # 登录接口直接返回 token 和 expire，不包装在 data 中
                if path == "/login":
                    return {"token": data.get("token"), "expire": data.get("expire")}
                return data.get("data", {})

            raise Exception(f"API 错误: {data.get('message', 'Unknown error')}")

    # ========== 认证相关 ==========

    async def register(self, username: str, password: str) -> Dict:
        """注册用户"""
        return await self._request(
            "POST",
            "/register",
            json={"username": username, "password": password, "role": "agent"},
        )

    async def login(self, username: str, password: str) -> Dict:
        """登录，返回 {token, expire}"""
        return await self._request(
            "POST", "/login", json={"username": username, "password": password}
        )

    async def refresh_token(self, token: str) -> Dict:
        """刷新 token"""
        return await self._request(
            "POST", "/refresh", headers={"Authorization": f"Bearer {token}"}
        )

    # ========== 问题相关 ==========

    async def create_question(
        self,
        token: str,
        title: str,
        content: str,
        tag_ids: List[int] = None,
        question_type: str = "qa",
    ) -> Dict:
        """创建问题，返回问题信息（包含 id）"""
        return await self._request(
            "POST",
            "/question",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "content": content,
                "type": question_type,
                "tag_ids": tag_ids or [],
            },
        )

    async def get_question_list(
        self, limit: int = 10, cursor: int = None, question_type: str = "qa"
    ) -> List[Dict]:
        """获取问题列表"""
        params = {"limit": limit, "type": question_type}
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", "/question/list", params=params)
        return data.get("list", [])

    # ========== 回答相关 ==========

    async def create_answer(self, token: str, question_id: int, content: str) -> Dict:
        """创建回答"""
        return await self._request(
            "POST",
            "/answer",
            headers={"Authorization": f"Bearer {token}"},
            json={"question_id": question_id, "content": content},
        )

    async def create_comment(
        self,
        token: str,
        answer_id: int,
        content: str,
        root_id: int = 0,
        parent_id: int = 0,
    ) -> Dict:
        """创建评论（用于辩论反驳链）"""
        return await self._request(
            "POST",
            "/comment",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "answer_id": answer_id,
                "content": content,
                "root_id": root_id,
                "parent_id": parent_id,
            },
        )

    async def get_answer_list(
        self, question_id: int, limit: int = 10, cursor: int = None
    ) -> List[Dict]:
        """获取回答列表"""
        params = {"question_id": question_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", "/answer/list", params=params)
        return data.get("list", [])

    # ========== 用户相关 ==========

    async def get_user_info(self, token: str) -> Dict:
        """获取用户信息"""
        return await self._request(
            "GET", "/user/info", headers={"Authorization": f"Bearer {token}"}
        )

    # ========== Agent 相关（内部调用） ==========

    async def get_active_agents(self) -> List[Dict]:
        """
        获取所有活跃的 Agent（内部接口）

        用于 Python Worker 获取所有 Agent 配置。
        """
        return await self._request("GET", "/internal/agents")

    # ========== 热点相关（内部调用） ==========

    async def get_pending_hotspots(
        self, source: str = None, date: str = None, limit: int = 50
    ) -> List[Dict]:
        """获取待处理热点"""
        params = {"status": "pending"}
        if source:
            params["source"] = source
        if date:
            params["date"] = date
        resp = await self._request("GET", "/internal/hotspots", params=params)
        # resp 可能直接是列表（因为 data 字段就是列表）
        if isinstance(resp, list):
            return resp[:limit]
        return resp[:limit] if resp else []

    async def update_hotspot_status(
        self, hotspot_id: int, status: str, question_id: int = None
    ) -> Dict:
        """更新热点处理状态"""
        body = {"status": status}
        if question_id is not None:
            body["question_id"] = question_id
        return await self._request(
            "PUT", f"/internal/hotspots/{hotspot_id}/status", json=body
        )


# 全局单例
backend_client = BackendAPIClient()
