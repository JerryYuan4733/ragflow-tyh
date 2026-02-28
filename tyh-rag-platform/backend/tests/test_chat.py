"""对话接口测试 (T-014)"""
import pytest
import httpx

BASE = "http://localhost:8000/api/v1"


class TestChat:
    token: str = ""
    session_id: str = ""

    @pytest.fixture(autouse=True)
    def client(self):
        self.c = httpx.Client(base_url=BASE, timeout=30)

    def _auth(self):
        return {"Authorization": f"Bearer {TestChat.token}"}

    def test_01_login(self):
        r = self.c.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        TestChat.token = r.json()["access_token"]

    def test_02_create_session(self):
        r = self.c.post("/chat/sessions", json={"title": "测试"}, headers=self._auth())
        assert r.status_code == 201
        TestChat.session_id = r.json()["id"]

    def test_03_list_sessions(self):
        r = self.c.get("/chat/sessions", headers=self._auth())
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_04_get_history(self):
        r = self.c.get(f"/chat/sessions/{TestChat.session_id}/messages", headers=self._auth())
        assert r.status_code == 200

    def test_05_suggestions(self):
        r = self.c.get("/chat/suggestions", headers=self._auth())
        assert r.status_code == 200

    def test_06_search(self):
        r = self.c.get("/chat/search?keyword=test", headers=self._auth())
        assert r.status_code == 200

    def test_07_delete_session(self):
        r = self.c.delete(f"/chat/sessions/{TestChat.session_id}", headers=self._auth())
        assert r.status_code == 200
