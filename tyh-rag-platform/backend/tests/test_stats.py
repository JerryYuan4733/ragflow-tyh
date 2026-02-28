"""统计接口测试 (T-042)"""
import pytest
import httpx

BASE = "http://localhost:8000/api/v1"


class TestStats:
    token: str = ""

    @pytest.fixture(autouse=True)
    def client(self):
        self.c = httpx.Client(base_url=BASE, timeout=30)

    def _auth(self):
        return {"Authorization": f"Bearer {TestStats.token}"}

    def test_01_login(self):
        r = self.c.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        TestStats.token = r.json()["access_token"]

    def test_02_overview(self):
        r = self.c.get("/stats/overview", headers=self._auth())
        assert r.status_code == 200
        d = r.json()
        assert "total_documents" in d
        assert "satisfaction_rate" in d

    def test_03_trends(self):
        r = self.c.get("/stats/trends?days=7", headers=self._auth())
        assert r.status_code == 200

    def test_04_top_questions(self):
        r = self.c.get("/stats/top-questions?limit=5", headers=self._auth())
        assert r.status_code == 200

    def test_05_roi(self):
        r = self.c.get("/stats/roi", headers=self._auth())
        assert r.status_code == 200
        assert "resolution_rate" in r.json()

    def test_06_coverage(self):
        r = self.c.get("/stats/coverage", headers=self._auth())
        assert r.status_code == 200

    def test_07_comparison(self):
        r = self.c.get("/stats/comparison", headers=self._auth())
        assert r.status_code == 200
