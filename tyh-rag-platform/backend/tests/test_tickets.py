"""工单接口测试 (T-025)"""
import pytest
import httpx

BASE = "http://localhost:8000/api/v1"


class TestTickets:
    token: str = ""

    @pytest.fixture(autouse=True)
    def client(self):
        self.c = httpx.Client(base_url=BASE, timeout=30)

    def _auth(self):
        return {"Authorization": f"Bearer {TestTickets.token}"}

    def test_01_login(self):
        r = self.c.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        TestTickets.token = r.json()["access_token"]

    def test_02_list_tickets(self):
        r = self.c.get("/tickets", headers=self._auth())
        assert r.status_code == 200

    def test_03_list_by_status(self):
        r = self.c.get("/tickets?status=pending", headers=self._auth())
        assert r.status_code == 200

    def test_04_get_ticket(self):
        """获取不存在的工单"""
        r = self.c.get("/tickets/nonexistent", headers=self._auth())
        assert r.status_code in (200, 404)

    def test_05_assign_ticket(self):
        """分配不存在的工单"""
        r = self.c.put("/tickets/nonexistent/assign", json={"assignee_id": "user1"}, headers=self._auth())
        assert r.status_code in (200, 404)
