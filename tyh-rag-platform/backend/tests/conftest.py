"""测试配置 - pytest fixtures"""

import pytest

try:
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    @pytest.fixture
    async def client():
        """异步测试客户端（集成测试用，需要完整 app 上下文）"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
except ImportError:
    pass  # 单元测试不需要完整 app 上下文
