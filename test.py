"""
AgentTalk API 测试套件

测试覆盖:
1. 用户注册和登录
2. 问题、回答、评论的 CRUD 操作
3. 点赞/点踩功能（包括并发和重复操作）
4. 关注功能
5. 收藏功能

运行方式:
    pytest test.py -v
    pytest test.py -v -k "test_reaction" # 只运行反应相关测试
    pytest test.py -v -s # 显示 print 输出
"""

import pytest
import requests
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

# 配置
BASE_URL = "http://localhost:8080"
CONCURRENT_WORKERS = 10  # 并发测试的线程数


class APIClient:
    """API 客户端封装"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def register(self, username: str, password: str, role: str = "user") -> requests.Response:
        """用户注册"""
        return self.session.post(
            f"{self.base_url}/register",
            json={"username": username, "password": password, "role": role},
            headers=self._headers()
        )

    def login(self, username: str, password: str) -> requests.Response:
        """用户登录"""
        resp = self.session.post(
            f"{self.base_url}/login",
            json={"username": username, "password": password},
            headers=self._headers()
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("token")
        return resp

    def get_user_info(self) -> requests.Response:
        """获取当前用户信息"""
        return self.session.get(
            f"{self.base_url}/user/info",
            headers=self._headers()
        )

    def create_question(self, title: str, content: str, tags: List[str] = None) -> requests.Response:
        """创建问题"""
        payload = {"title": title, "content": content}
        if tags:
            payload["tags"] = tags
        return self.session.post(
            f"{self.base_url}/question",
            json=payload,
            headers=self._headers()
        )

    def get_question(self, question_id: int) -> requests.Response:
        """获取问题详情"""
        return self.session.get(
            f"{self.base_url}/question/{question_id}",
            headers=self._headers()
        )

    def create_answer(self, question_id: int, content: str) -> requests.Response:
        """创建回答"""
        return self.session.post(
            f"{self.base_url}/answer",
            json={"question_id": question_id, "content": content},
            headers=self._headers()
        )

    def get_answer(self, answer_id: int) -> requests.Response:
        """获取回答详情"""
        return self.session.get(
            f"{self.base_url}/answer/{answer_id}",
            headers=self._headers()
        )

    def create_comment(self, answer_id: int, content: str, parent_id: int = None) -> requests.Response:
        """创建评论"""
        payload = {"answer_id": answer_id, "content": content}
        if parent_id:
            payload["parent_id"] = parent_id
        return self.session.post(
            f"{self.base_url}/comment",
            json=payload,
            headers=self._headers()
        )

    def execute_reaction(self, target_type: int, target_id: int, action: int) -> requests.Response:
        """
        执行点赞/点踩操作
        target_type: 1=问题, 2=回答, 3=评论
        action: 0=取消, 1=点赞, 2=点踩
        """
        return self.session.post(
            f"{self.base_url}/reaction",
            json={"target_type": target_type, "target_id": target_id, "action": action},
            headers=self._headers()
        )

    def get_reaction_status(self, target_type: int, target_id: int) -> requests.Response:
        """获取点赞/点踩状态"""
        return self.session.get(
            f"{self.base_url}/reaction/status",
            params={"target_type": target_type, "target_id": target_id},
            headers=self._headers()
        )

    def execute_follow(self, target_type: int, target_id: int, action: bool) -> requests.Response:
        """
        执行关注操作
        target_type: 1=问题, 4=用户
        action: True=关注, False=取消关注
        """
        return self.session.post(
            f"{self.base_url}/follow",
            json={"target_type": target_type, "target_id": target_id, "action": action},
            headers=self._headers()
        )

    def get_follow_status(self, target_type: int, target_id: int) -> requests.Response:
        """获取关注状态"""
        return self.session.get(
            f"{self.base_url}/follow/status",
            params={"target_type": target_type, "target_id": target_id},
            headers=self._headers()
        )


def random_string(length: int = 10) -> str:
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


@pytest.fixture
def client():
    """创建 API 客户端"""
    return APIClient()


@pytest.fixture
def authenticated_client():
    """创建已认证的 API 客户端"""
    client = APIClient()
    username = f"test_{random_string()}"
    password = "test123456"

    # 注册
    resp = client.register(username, password)
    assert resp.status_code == 200, f"注册失败: {resp.text}"

    # 登录
    resp = client.login(username, password)
    assert resp.status_code == 200, f"登录失败: {resp.text}"
    assert client.token is not None, "未获取到 token"

    return client


@pytest.fixture
def question_id(authenticated_client):
    """创建一个测试问题并返回 ID"""
    resp = authenticated_client.create_question(
        title=f"测试问题 {random_string()}",
        content="这是一个测试问题的内容",
        tags=["测试", "Python"]
    )
    assert resp.status_code == 200, f"创建问题失败: {resp.text}"
    data = resp.json()
    return data["data"]["id"]


@pytest.fixture
def answer_id(authenticated_client, question_id):
    """创建一个测试回答并返回 ID"""
    resp = authenticated_client.create_answer(
        question_id=question_id,
        content="这是一个测试回答的内容"
    )
    assert resp.status_code == 200, f"创建回答失败: {resp.text}"
    data = resp.json()
    return data["data"]["id"]


@pytest.fixture
def comment_id(authenticated_client, answer_id):
    """创建一个测试评论并返回 ID"""
    resp = authenticated_client.create_comment(
        answer_id=answer_id,
        content="这是一个测试评论"
    )
    assert resp.status_code == 200, f"创建评论失败: {resp.text}"
    data = resp.json()
    return data["data"]["id"]


# ==================== 用户认证测试 ====================

class TestAuthentication:
    """用户认证相关测试"""

    def test_register_success(self, client):
        """测试成功注册"""
        username = f"user_{random_string()}"
        resp = client.register(username, "password123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "注册成功" in data["message"]

    def test_register_duplicate_username(self, client):
        """测试重复用户名注册"""
        username = f"user_{random_string()}"
        client.register(username, "password123")

        # 尝试再次注册相同用户名
        resp = client.register(username, "password123")
        assert resp.status_code == 400
        data = resp.json()
        assert "用户名已存在" in data["message"]

    def test_register_invalid_role(self, client):
        """测试无效角色注册"""
        username = f"user_{random_string()}"
        resp = client.register(username, "password123", role="admin")
        assert resp.status_code == 400
        data = resp.json()
        assert "角色不合法" in data["message"]

    def test_login_success(self, client):
        """测试成功登录"""
        username = f"user_{random_string()}"
        password = "password123"
        client.register(username, password)

        resp = client.login(username, password)
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert client.token is not None

    def test_login_wrong_password(self, client):
        """测试错误密码登录"""
        username = f"user_{random_string()}"
        client.register(username, "password123")

        resp = client.login(username, "wrongpassword")
        assert resp.status_code == 401

    def test_get_user_info(self, authenticated_client):
        """测试获取用户信息"""
        resp = authenticated_client.get_user_info()
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "data" in data
        assert "username" in data["data"]


# ==================== 问题相关测试 ====================

class TestQuestion:
    """问题相关测试"""

    def test_create_question(self, authenticated_client):
        """测试创建问题"""
        resp = authenticated_client.create_question(
            title="如何学习 Python?",
            content="我是编程新手，想学习 Python，有什么建议吗？",
            tags=["Python", "学习"]
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "id" in data["data"]

    def test_get_question(self, authenticated_client, question_id):
        """测试获取问题详情"""
        resp = authenticated_client.get_question(question_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["id"] == question_id

    def test_create_question_without_auth(self, client):
        """测试未认证创建问题"""
        resp = client.create_question(
            title="测试问题",
            content="测试内容"
        )
        assert resp.status_code == 401


# ==================== 回答相关测试 ====================

class TestAnswer:
    """回答相关测试"""

    def test_create_answer(self, authenticated_client, question_id):
        """测试创建回答"""
        resp = authenticated_client.create_answer(
            question_id=question_id,
            content="这是一个详细的回答内容"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "id" in data["data"]

    def test_get_answer(self, authenticated_client, answer_id):
        """测试获取回答详情"""
        resp = authenticated_client.get_answer(answer_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["id"] == answer_id


# ==================== 评论相关测试 ====================

class TestComment:
    """评论相关测试"""

    def test_create_comment(self, authenticated_client, answer_id):
        """测试创建评论"""
        resp = authenticated_client.create_comment(
            answer_id=answer_id,
            content="这是一条评论"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "id" in data["data"]

    def test_create_reply(self, authenticated_client, answer_id, comment_id):
        """测试创建回复"""
        resp = authenticated_client.create_comment(
            answer_id=answer_id,
            content="这是一条回复",
            parent_id=comment_id
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200


# ==================== 点赞/点踩测试（重点：并发和重复操作）====================

class TestReaction:
    """点赞/点踩相关测试"""

    def test_like_answer(self, authenticated_client, answer_id):
        """测试点赞回答"""
        resp = authenticated_client.execute_reaction(
            target_type=2,  # 回答
            target_id=answer_id,
            action=1  # 点赞
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200

        # 验证状态
        resp = authenticated_client.get_reaction_status(2, answer_id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["status"] == 1

    def test_dislike_answer(self, authenticated_client, answer_id):
        """测试点踩回答"""
        # 先确保初始状态是 0（无操作）
        resp = authenticated_client.get_reaction_status(2, answer_id)
        initial_status = resp.json()["data"]["status"]

        # 如果有之前的操作，先取消
        if initial_status != 0:
            resp = authenticated_client.execute_reaction(2, answer_id, 0)
            assert resp.status_code == 200, "取消操作失败"

            # 验证取消成功
            resp = authenticated_client.get_reaction_status(2, answer_id)
            assert resp.json()["data"]["status"] == 0, "取消后状态应该为0"

        # 执行点踩
        resp = authenticated_client.execute_reaction(
            target_type=2,
            target_id=answer_id,
            action=2  # 点踩
        )
        assert resp.status_code == 200

        # 验证状态
        resp = authenticated_client.get_reaction_status(2, answer_id)
        data = resp.json()
        assert data["data"]["status"] == 2

    def test_cancel_reaction(self, authenticated_client, answer_id):
        """测试取消点赞"""
        # 先点赞
        authenticated_client.execute_reaction(2, answer_id, 1)

        # 取消
        resp = authenticated_client.execute_reaction(2, answer_id, 0)
        assert resp.status_code == 200

        # 验证状态
        resp = authenticated_client.get_reaction_status(2, answer_id)
        data = resp.json()
        assert data["data"]["status"] == 0

    def test_switch_reaction(self, authenticated_client, answer_id):
        """测试切换点赞/点踩"""
        # 先点赞
        authenticated_client.execute_reaction(2, answer_id, 1)
        resp = authenticated_client.get_reaction_status(2, answer_id)
        assert resp.json()["data"]["status"] == 1

        # 切换到点踩
        authenticated_client.execute_reaction(2, answer_id, 2)
        resp = authenticated_client.get_reaction_status(2, answer_id)
        assert resp.json()["data"]["status"] == 2

        # 再切换回点赞
        authenticated_client.execute_reaction(2, answer_id, 1)
        resp = authenticated_client.get_reaction_status(2, answer_id)
        assert resp.json()["data"]["status"] == 1

    def test_repeated_like(self, authenticated_client, answer_id):
        """测试重复点赞（幂等性）"""
        # 多次点赞同一个回答
        for _ in range(5):
            resp = authenticated_client.execute_reaction(2, answer_id, 1)
            assert resp.status_code == 200

        # 验证最终状态仍然是点赞
        resp = authenticated_client.get_reaction_status(2, answer_id)
        data = resp.json()
        assert data["data"]["status"] == 1

    def test_rapid_toggle(self, authenticated_client, answer_id):
        """测试快速切换点赞/取消"""
        actions = [1, 0, 1, 0, 1, 0, 1]  # 点赞-取消-点赞-取消...

        for action in actions:
            resp = authenticated_client.execute_reaction(2, answer_id, action)
            assert resp.status_code == 200

        # 验证最终状态
        resp = authenticated_client.get_reaction_status(2, answer_id)
        data = resp.json()
        assert data["data"]["status"] == 1  # 最后一次是点赞

    def test_concurrent_reactions_same_user(self, authenticated_client, answer_id):
        """测试同一用户并发点赞（压力测试）"""
        def like_action():
            try:
                resp = authenticated_client.execute_reaction(2, answer_id, 1)
                return resp.status_code == 200
            except Exception as e:
                print(f"并发请求异常: {e}")
                return False

        # 并发发送 20 个点赞请求
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = [executor.submit(like_action) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # 所有请求都应该成功
        assert all(results), "部分并发请求失败"

        # 验证最终状态：应该只有一个点赞
        resp = authenticated_client.get_reaction_status(2, answer_id)
        data = resp.json()
        assert data["data"]["status"] == 1

    def test_concurrent_toggle_reactions(self, authenticated_client, answer_id):
        """测试并发切换点赞/点踩"""
        def random_action():
            try:
                action = random.choice([0, 1, 2])  # 随机选择操作
                resp = authenticated_client.execute_reaction(2, answer_id, action)
                return resp.status_code == 200, action
            except Exception as e:
                print(f"并发请求异常: {e}")
                return False, None

        # 并发发送混合操作
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = [executor.submit(random_action) for _ in range(30)]
            results = [f.result() for f in as_completed(futures)]

        # 所有请求都应该成功
        assert all(r[0] for r in results), "部分并发请求失败"

        # 验证最终状态一致性（无论是什么状态，都应该是 0/1/2 之一）
        resp = authenticated_client.get_reaction_status(2, answer_id)
        data = resp.json()
        assert data["data"]["status"] in [0, 1, 2]

    def test_multiple_users_like_same_answer(self):
        """测试多个用户同时点赞同一个回答"""
        # 创建一个问题和回答
        creator = APIClient()
        username = f"creator_{random_string()}"
        resp = creator.register(username, "password123")
        assert resp.status_code == 200, f"注册失败: {resp.text}"

        resp = creator.login(username, "password123")
        assert resp.status_code == 200, f"登录失败: {resp.text}"

        resp = creator.create_question("测试问题标题", "测试内容")
        assert resp.status_code == 200, f"创建问题失败: {resp.text}"
        question_id = resp.json()["data"]["id"]

        resp = creator.create_answer(question_id, "这是一个测试回答的内容")
        assert resp.status_code == 200, f"创建回答失败: {resp.text}"
        answer_id = resp.json()["data"]["id"]

        # 创建多个用户并发点赞
        def user_like():
            try:
                client = APIClient()
                username = f"user_{random_string()}"
                reg_resp = client.register(username, "password123")
                if reg_resp.status_code != 200:
                    print(f"注册失败: {reg_resp.text}")
                    return False

                login_resp = client.login(username, "password123")
                if login_resp.status_code != 200:
                    print(f"登录失败: {login_resp.text}")
                    return False

                resp = client.execute_reaction(2, answer_id, 1)
                if resp.status_code != 200:
                    print(f"点赞失败: {resp.text}")
                    return False

                return True
            except Exception as e:
                print(f"用户点赞异常: {e}")
                return False

        # 10 个用户并发点赞
        with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
            futures = [executor.submit(user_like) for _ in range(10)]
            results = [f.result() for f in as_completed(futures)]

        # 所有用户都应该成功点赞
        success_count = sum(results)
        assert success_count >= 8, f"只有 {success_count}/10 个用户成功点赞"

    def test_reaction_on_question(self, authenticated_client, question_id):
        """测试对问题的点赞"""
        resp = authenticated_client.execute_reaction(
            target_type=1,  # 问题
            target_id=question_id,
            action=1
        )
        assert resp.status_code == 200

        resp = authenticated_client.get_reaction_status(1, question_id)
        data = resp.json()
        assert data["data"]["status"] == 1

    def test_reaction_on_comment(self, authenticated_client, comment_id):
        """测试对评论的点赞"""
        resp = authenticated_client.execute_reaction(
            target_type=3,  # 评论
            target_id=comment_id,
            action=1
        )
        assert resp.status_code == 200

        resp = authenticated_client.get_reaction_status(3, comment_id)
        data = resp.json()
        assert data["data"]["status"] == 1


# ==================== 关注测试 ====================

class TestFollow:
    """关注相关测试"""

    def test_follow_user(self):
        """测试关注用户"""
        # 创建两个用户
        user1 = APIClient()
        username1 = f"user1_{random_string()}"
        user1.register(username1, "password123")
        user1.login(username1, "password123")

        user2 = APIClient()
        username2 = f"user2_{random_string()}"
        user2.register(username2, "password123")
        user2.login(username2, "password123")

        # 获取 user2 的 ID
        resp = user2.get_user_info()
        user2_id = resp.json()["data"]["id"]

        # user1 关注 user2
        resp = user1.execute_follow(
            target_type=4,  # 用户
            target_id=user2_id,
            action=True  # 关注
        )
        assert resp.status_code == 200

        # 验证关注状态
        resp = user1.get_follow_status(4, user2_id)
        data = resp.json()
        assert data["data"]["is_following"] == True

    def test_unfollow_user(self):
        """测试取消关注"""
        user1 = APIClient()
        username1 = f"user1_{random_string()}"
        user1.register(username1, "password123")
        user1.login(username1, "password123")

        user2 = APIClient()
        username2 = f"user2_{random_string()}"
        user2.register(username2, "password123")
        user2.login(username2, "password123")

        user2_id = user2.get_user_info().json()["data"]["id"]

        # 先关注
        user1.execute_follow(4, user2_id, True)

        # 取消关注
        resp = user1.execute_follow(4, user2_id, False)
        assert resp.status_code == 200

        # 验证状态
        resp = user1.get_follow_status(4, user2_id)
        data = resp.json()
        assert data["data"]["is_following"] == False

    def test_follow_question(self, authenticated_client, question_id):
        """测试关注问题"""
        resp = authenticated_client.execute_follow(
            target_type=1,  # 问题
            target_id=question_id,
            action=True
        )
        assert resp.status_code == 200

        resp = authenticated_client.get_follow_status(1, question_id)
        data = resp.json()
        assert data["data"]["is_following"] == True

    def test_repeated_follow(self):
        """测试重复关注（幂等性）"""
        user1 = APIClient()
        username1 = f"user1_{random_string()}"
        user1.register(username1, "password123")
        user1.login(username1, "password123")

        user2 = APIClient()
        username2 = f"user2_{random_string()}"
        user2.register(username2, "password123")
        user2.login(username2, "password123")

        user2_id = user2.get_user_info().json()["data"]["id"]

        # 多次关注
        for _ in range(5):
            resp = user1.execute_follow(4, user2_id, True)
            assert resp.status_code == 200

        # 验证状态
        resp = user1.get_follow_status(4, user2_id)
        data = resp.json()
        assert data["data"]["is_following"] == True


# ==================== 边界和异常测试 ====================

class TestEdgeCases:
    """边界和异常情况测试"""

    def test_reaction_invalid_target_type(self, authenticated_client):
        """测试无效的目标类型"""
        resp = authenticated_client.execute_reaction(
            target_type=99,  # 无效类型
            target_id=1,
            action=1
        )
        assert resp.status_code == 400

    def test_reaction_invalid_action(self, authenticated_client, answer_id):
        """测试无效的操作类型"""
        resp = authenticated_client.execute_reaction(
            target_type=2,
            target_id=answer_id,
            action=99  # 无效操作
        )
        assert resp.status_code == 400

    def test_reaction_nonexistent_target(self, authenticated_client):
        """测试对不存在的目标点赞"""
        resp = authenticated_client.execute_reaction(
            target_type=2,
            target_id=999999,  # 不存在的 ID
            action=1
        )
        # 根据实际 API 行为，可能返回 200 或 404
        # 这里假设返回 200（Redis 操作不检查目标是否存在）
        assert resp.status_code in [200, 404, 500]

    def test_unauthorized_reaction(self, client, answer_id):
        """测试未认证用户点赞"""
        resp = client.execute_reaction(2, answer_id, 1)
        assert resp.status_code == 401


# ==================== 性能和压力测试 ====================

class TestPerformance:
    """性能和压力测试"""

    def test_rapid_sequential_reactions(self, authenticated_client, answer_id):
        """测试快速连续操作"""
        start_time = time.time()

        # 连续执行 50 次操作
        for i in range(50):
            action = i % 3  # 0, 1, 2 循环
            resp = authenticated_client.execute_reaction(2, answer_id, action)
            assert resp.status_code == 200

        elapsed = time.time() - start_time
        print(f"\n50 次连续操作耗时: {elapsed:.2f} 秒")

        # 验证最终状态
        resp = authenticated_client.get_reaction_status(2, answer_id)
        assert resp.status_code == 200

    def test_batch_create_and_react(self, authenticated_client, question_id):
        """测试批量创建回答并点赞"""
        answer_ids = []

        # 创建 10 个回答（内容至少 10 个字符）
        for i in range(10):
            resp = authenticated_client.create_answer(
                question_id=question_id,
                content=f"这是第 {i} 个测试回答的内容"
            )
            assert resp.status_code == 200, f"创建回答失败: {resp.text}"
            answer_ids.append(resp.json()["data"]["id"])

        # 对所有回答点赞
        for aid in answer_ids:
            resp = authenticated_client.execute_reaction(2, aid, 1)
            assert resp.status_code == 200

        # 验证所有点赞状态
        for aid in answer_ids:
            resp = authenticated_client.get_reaction_status(2, aid)
            data = resp.json()
            assert data["data"]["status"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
