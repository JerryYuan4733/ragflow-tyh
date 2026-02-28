"""健康检查接口测试"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查接口返回200"""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "knowledge-base-api"
