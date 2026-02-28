"""健康检查接口"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """K8S liveness/readiness 探针"""
    return {
        "status": "healthy",
        "service": "knowledge-base-api",
        "version": "1.0.0",
    }
