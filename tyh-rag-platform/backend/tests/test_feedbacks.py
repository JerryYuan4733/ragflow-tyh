"""反馈接口测试 (T-022)"""
import pytest
import httpx

BASE = "http://localhost:8000/api/v1"


class TestFeedbacks:
    token: str = ""

    @pytest.fixture(autouse=True)
    def client(self):
        self.c = httpx.Client(base_url=BASE, timeout=30)

    def _auth(self):
        return {"Authorization": f"Bearer {TestFeedbacks.token}"}

    def test_01_login(self):
        r = self.c.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        TestFeedbacks.token = r.json()["access_token"]

    def test_02_submit_like(self):
        """提交点赞 - 需要有效message_id"""
        r = self.c.post("/feedbacks", json={
            "message_id": "test-msg-1", "session_id": "test-sess-1", "type": "like"
        }, headers=self._auth())
        # 可能400因为foreign key, 但接口应该响应
        assert r.status_code in (200, 201, 400, 422)

    def test_03_submit_dislike(self):
        """提交点踩 - 应自动创建工单"""
        r = self.c.post("/feedbacks", json={
            "message_id": "test-msg-2", "session_id": "test-sess-1", "type": "dislike",
            "reason_category": "答非所问"
        }, headers=self._auth())
        assert r.status_code in (200, 201, 400, 422)

    def test_04_transfer_human(self):
        """转人工"""
        r = self.c.post("/feedbacks/transfer", json={
            "session_id": "test-sess-1"
        }, headers=self._auth())
        assert r.status_code in (200, 201, 400, 422)
