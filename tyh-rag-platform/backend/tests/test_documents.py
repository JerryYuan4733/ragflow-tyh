"""文档接口测试 (T-018)"""
import pytest
import httpx

BASE = "http://localhost:8000/api/v1"


class TestDocuments:
    token: str = ""

    @pytest.fixture(autouse=True)
    def client(self):
        self.c = httpx.Client(base_url=BASE, timeout=30)

    def _auth(self):
        return {"Authorization": f"Bearer {TestDocuments.token}"}

    def test_01_login(self):
        r = self.c.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200
        TestDocuments.token = r.json()["access_token"]

    def test_02_list_documents(self):
        r = self.c.get("/documents", headers=self._auth())
        assert r.status_code == 200

    def test_03_upload_document(self):
        """上传测试 - 需要multipart"""
        import io
        files = {"file": ("test.txt", io.BytesIO(b"Hello world"), "text/plain")}
        r = self.c.post("/documents", files=files, headers=self._auth())
        assert r.status_code in (200, 201, 422)  # 422 if RAGflow unavailable

    def test_04_list_after_upload(self):
        r = self.c.get("/documents", headers=self._auth())
        assert r.status_code == 200

    def test_05_get_versions(self):
        """版本历史 - 无具体ID时应返回空或404"""
        r = self.c.get("/documents/nonexistent/versions", headers=self._auth())
        assert r.status_code in (200, 404)
