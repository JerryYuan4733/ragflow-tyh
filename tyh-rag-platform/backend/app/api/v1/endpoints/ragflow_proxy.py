"""RAGFlow 代理接口 - 供前端拉取 RAGFlow 助手/知识库列表"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_it_admin
from app.db.session import get_db
from app.models import User
from app.adapters.ragflow_client import ragflow_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/assistants")
async def list_ragflow_assistants(
    _: User = Depends(require_it_admin),
):
    """获取 RAGFlow 助手列表（仅IT管理员）
    
    用于团队配置页面选择助手绑定。
    """
    try:
        assistants = await ragflow_client.list_chat_assistants()
        return {
            "items": [
                {
                    "id": a.id,
                    "name": a.name,
                }
                for a in assistants
            ],
            "total": len(assistants),
        }
    except Exception as e:
        logger.error(f"获取 RAGFlow 助手列表失败: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 RAGFlow: {str(e)}"
        )


@router.get("/datasets")
async def list_ragflow_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    _: User = Depends(require_it_admin),
):
    """获取 RAGFlow 知识库列表（仅IT管理员）
    
    用于团队配置页面选择知识库绑定。
    """
    try:
        datasets = await ragflow_client.list_datasets(page=page, size=page_size)
        return {
            "items": [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "description": getattr(ds, "description", None),
                    "document_count": getattr(ds, "document_count", 0),
                    "chunk_count": getattr(ds, "chunk_count", 0),
                }
                for ds in datasets
            ],
            "total": len(datasets),
        }
    except Exception as e:
        logger.error(f"获取 RAGFlow 知识库列表失败: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 RAGFlow: {str(e)}"
        )


@router.get("/assistants/{assistant_id}")
async def get_ragflow_assistant(
    assistant_id: str,
    _: User = Depends(require_it_admin),
):
    """获取 RAGFlow 助手详情（仅IT管理员）"""
    try:
        assistant = await ragflow_client.get_chat_assistant(assistant_id)
        if not assistant:
            raise HTTPException(status_code=404, detail="助手不存在")

        llm = assistant.get("llm", {}) or {}
        raw_datasets = assistant.get("datasets", []) or []
        ds_ids = [d["id"] for d in raw_datasets if isinstance(d, dict) and "id" in d]

        return {
            "id": assistant.get("id"),
            "name": assistant.get("name"),
            "description": assistant.get("description"),
            "llm_model": llm.get("model_name"),
            "dataset_ids": ds_ids,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 RAGFlow 助手详情失败: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 RAGFlow: {str(e)}"
        )
