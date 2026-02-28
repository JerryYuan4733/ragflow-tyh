"""
端到端集成测试 (T-061)
7核心场景: 登录→对话→文档→QA→反馈→工单→统计
"""

import pytest
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"
ADMIN = {"username": "admin", "password": "admin123"}


class TestE2E:
    """端到端集成测试"""

    token: str = ""
    session_id: str = ""
    message_id: str = ""
    doc_id: str = ""
    qa_id: str = ""
    ticket_id: str = ""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = httpx.Client(base_url=BASE_URL, timeout=30)

    # ========== S1: 认证 ==========

    def test_01_login(self):
        """登录获取token"""
        res = self.client.post("/auth/login", json=ADMIN)
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        TestE2E.token = data["access_token"]

    def test_02_get_me(self):
        """获取当前用户"""
        res = self.client.get("/auth/me", headers=self._auth())
        assert res.status_code == 200
        assert res.json()["username"] == "admin"

    # ========== S2: 对话 ==========

    def test_03_create_session(self):
        """创建对话会话"""
        res = self.client.post("/chat/sessions", json={"title": "测试对话"}, headers=self._auth())
        assert res.status_code == 201
        TestE2E.session_id = res.json()["id"]

    def test_04_list_sessions(self):
        """获取会话列表"""
        res = self.client.get("/chat/sessions", headers=self._auth())
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    def test_05_get_suggestions(self):
        """获取推荐问题"""
        res = self.client.get("/chat/suggestions", headers=self._auth())
        assert res.status_code == 200
        assert len(res.json()["questions"]) > 0

    def test_06_get_history(self):
        """获取历史消息"""
        res = self.client.get(f"/chat/sessions/{TestE2E.session_id}/messages", headers=self._auth())
        assert res.status_code == 200

    def test_07_delete_session(self):
        """删除会话"""
        res = self.client.delete(f"/chat/sessions/{TestE2E.session_id}", headers=self._auth())
        assert res.status_code == 200

    # ========== S3: 文档管理 ==========

    def test_08_list_documents(self):
        """文档列表"""
        res = self.client.get("/documents", headers=self._auth())
        assert res.status_code == 200

    # ========== S4: Q&A管理 ==========

    def test_09_create_qa(self):
        """创建Q&A"""
        res = self.client.post("/qa-pairs", json={
            "question": "测试问题", "answer": "测试答案"
        }, headers=self._auth())
        assert res.status_code == 201
        TestE2E.qa_id = res.json()["id"]

    def test_10_list_qa(self):
        """Q&A列表"""
        res = self.client.get("/qa-pairs", headers=self._auth())
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    def test_11_update_qa(self):
        """更新Q&A"""
        res = self.client.put(f"/qa-pairs/{TestE2E.qa_id}", json={
            "answer": "更新后的答案"
        }, headers=self._auth())
        assert res.status_code == 200

    def test_12_delete_qa(self):
        """删除Q&A"""
        res = self.client.delete(f"/qa-pairs/{TestE2E.qa_id}", headers=self._auth())
        assert res.status_code == 200

    # ========== S5: 工单管理 ==========

    def test_13_list_tickets(self):
        """工单列表"""
        res = self.client.get("/tickets", headers=self._auth())
        assert res.status_code == 200

    # ========== S6: 统计 ==========

    def test_14_stats_overview(self):
        """统计概览"""
        res = self.client.get("/stats/overview", headers=self._auth())
        assert res.status_code == 200
        data = res.json()
        assert "total_documents" in data
        assert "satisfaction_rate" in data

    def test_15_stats_trends(self):
        """对话趋势"""
        res = self.client.get("/stats/trends?days=7", headers=self._auth())
        assert res.status_code == 200

    def test_16_stats_roi(self):
        """ROI指标"""
        res = self.client.get("/stats/roi", headers=self._auth())
        assert res.status_code == 200
        assert "resolution_rate" in res.json()

    # ========== S7: 系统设置 ==========

    def test_17_get_chat_config(self):
        """获取对话配置"""
        res = self.client.get("/settings/chat-config", headers=self._auth())
        assert res.status_code == 200
        assert "temperature" in res.json()

    def test_18_get_announcements(self):
        """获取公告"""
        res = self.client.get("/announcements/active", headers=self._auth())
        assert res.status_code == 200

    def test_19_health_check(self):
        """健康检查"""
        res = self.client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    # ========== Helpers ==========

    def _auth(self):
        return {"Authorization": f"Bearer {TestE2E.token}"}
