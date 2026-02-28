"""
性能压测配置 (T-062)
Locust - 20并发, AI对话P99<=2s
运行: locust -f tests/locustfile.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between


class KBUser(HttpUser):
    wait_time = between(1, 3)
    token = ""

    def on_start(self):
        """登录获取token"""
        res = self.client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "admin123",
        })
        if res.status_code == 200:
            self.token = res.json()["access_token"]

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def health_check(self):
        """健康检查 (高频)"""
        self.client.get("/api/v1/health")

    @task(5)
    def list_sessions(self):
        """获取会话列表"""
        self.client.get("/api/v1/chat/sessions", headers=self._headers())

    @task(2)
    def get_suggestions(self):
        """获取推荐问题"""
        self.client.get("/api/v1/chat/suggestions", headers=self._headers())

    @task(1)
    def stats_overview(self):
        """统计概览"""
        self.client.get("/api/v1/stats/overview", headers=self._headers())

    @task(1)
    def list_documents(self):
        """文档列表"""
        self.client.get("/api/v1/documents", headers=self._headers())

    @task(1)
    def list_qa(self):
        """Q&A列表"""
        self.client.get("/api/v1/qa-pairs", headers=self._headers())

    @task(1)
    def get_notifications(self):
        """通知列表"""
        self.client.get("/api/v1/notifications", headers=self._headers())

    @task(1)
    def search_messages(self):
        """搜索消息"""
        self.client.get("/api/v1/chat/search?keyword=测试", headers=self._headers())
