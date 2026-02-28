"""Q&A接口测试 (T-020)"""
import pytest
import httpx

BASE = "http://localhost:8000/api/v1"


class TestQA:
    token: str = ""
    qa_id: str = ""

    @pytest.fixture(autouse=True)
    def client(self):
        self.c = httpx.Client(base_url=BASE, timeout=30)

    def _auth(self):
        return {"Authorization": f"Bearer {TestQA.token}"}

    def test_01_login(self):
        r = self.c.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        TestQA.token = r.json()["access_token"]

    def test_02_create_qa(self):
        r = self.c.post("/qa-pairs", json={"question": "Q测试", "answer": "A测试"}, headers=self._auth())
        assert r.status_code == 201
        TestQA.qa_id = r.json()["id"]

    def test_03_list_qa(self):
        r = self.c.get("/qa-pairs", headers=self._auth())
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_04_update_qa(self):
        r = self.c.put(f"/qa-pairs/{TestQA.qa_id}", json={"answer": "更新"}, headers=self._auth())
        assert r.status_code == 200

    def test_05_versions(self):
        r = self.c.get(f"/qa-pairs/{TestQA.qa_id}/versions", headers=self._auth())
        assert r.status_code == 200

    def test_06_download_template(self):
        r = self.c.get("/qa-pairs/template", headers=self._auth())
        assert r.status_code == 200

    def test_07_delete_qa(self):
        r = self.c.delete(f"/qa-pairs/{TestQA.qa_id}", headers=self._auth())
        assert r.status_code == 200
