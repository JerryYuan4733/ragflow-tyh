"""
文档同步服务

负责从 RAGFlow 全量同步文档到本地 document_meta 表。
核心逻辑：并行拉取各 dataset 文档列表 → HashMap 对比 → INSERT/UPDATE/标记异常

参考架构文档: docs/architecture/2026-02-25-1921-文档管理功能优化-架构设计-V1.md §4.5, §9
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.ragflow_client import RAGflowClient
from app.adapters.ragflow_types import DocumentInfo
from app.models import DocumentMeta, TeamDataset
from app.services.document_status import map_ragflow_status, STATUS_ERROR

logger = logging.getLogger(__name__)

# 同步时从 RAGFlow 拉取的最大文档数
SYNC_PAGE_SIZE = 9999


class DocumentSyncService:
    """文档同步服务（单例）"""

    def __init__(self, ragflow_client: RAGflowClient):
        self._ragflow_client = ragflow_client

    async def sync_dataset(
        self,
        db: AsyncSession,
        team_id: str,
        dataset_id: str,
        dataset_name: str = "",
        user_id: str = "system",
    ) -> dict:
        """同步单个 dataset 的文档

        Args:
            db: 数据库会话
            team_id: 团队 ID
            dataset_id: RAGFlow 知识库 ID
            dataset_name: 知识库名称（用于日志和返回）

        Returns:
            {"dataset_id", "dataset_name", "ragflow_count", "new", "updated", "orphans"}
        """
        # 1. 从 RAGFlow 拉取全量文档列表
        try:
            rf_docs = await self._ragflow_client.list_documents(
                dataset_id, page=1, size=SYNC_PAGE_SIZE
            )
        except Exception as e:
            logger.error(f"同步失败 - 拉取 RAGFlow 文档列表出错 (dataset={dataset_id}): {e}")
            raise

        # 2. 构建 RAGFlow 文档 HashMap（key = ragflow_document_id）
        rf_map: dict[str, DocumentInfo] = {doc.id: doc for doc in rf_docs}

        # 3. 查询本地 document_meta
        result = await db.execute(
            select(DocumentMeta).where(
                DocumentMeta.team_id == team_id,
                DocumentMeta.ragflow_dataset_id == dataset_id,
            )
        )
        local_docs = list(result.scalars().all())
        local_map: dict[str, DocumentMeta] = {
            doc.ragflow_document_id: doc
            for doc in local_docs
            if doc.ragflow_document_id
        }

        now = datetime.now(timezone.utc)
        new_count = 0
        updated_count = 0
        orphan_count = 0

        # 4. RAGFlow 有 + 本地无 → INSERT 新记录
        for rf_id, rf_doc in rf_map.items():
            if rf_id not in local_map:
                new_doc = DocumentMeta(
                    id=str(uuid.uuid4()),
                    team_id=team_id,
                    uploaded_by=user_id,
                    filename=rf_doc.name,
                    file_type=rf_doc.type or "application/octet-stream",
                    file_size=rf_doc.size,
                    category_path="/",
                    ragflow_document_id=rf_id,
                    ragflow_dataset_id=dataset_id,
                    status=map_ragflow_status(rf_doc.run),
                    run=rf_doc.run,
                    progress=rf_doc.progress,
                    last_synced_at=now,
                )
                db.add(new_doc)
                new_count += 1

        # 5. 两边都有 → UPDATE 状态
        for rf_id, rf_doc in rf_map.items():
            if rf_id in local_map:
                local_doc = local_map[rf_id]
                local_doc.status = map_ragflow_status(rf_doc.run)
                local_doc.run = rf_doc.run
                local_doc.progress = rf_doc.progress
                local_doc.last_synced_at = now
                # 如果文件名发生变化也同步
                if rf_doc.name and rf_doc.name != local_doc.filename:
                    local_doc.filename = rf_doc.name
                updated_count += 1

        # 6. 本地有 + RAGFlow 无 → 标记异常
        for local_doc in local_docs:
            if local_doc.ragflow_document_id and local_doc.ragflow_document_id not in rf_map:
                local_doc.status = STATUS_ERROR
                local_doc.last_synced_at = now
                orphan_count += 1

        logger.info(
            f"同步完成 dataset={dataset_id}: "
            f"RAGFlow={len(rf_docs)}, 新增={new_count}, "
            f"更新={updated_count}, 异常={orphan_count}"
        )

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset_name,
            "ragflow_count": len(rf_docs),
            "new": new_count,
            "updated": updated_count,
            "orphans": orphan_count,
        }

    async def sync_all_datasets(
        self,
        db: AsyncSession,
        team_id: str,
        user_id: str = "system",
    ) -> dict:
        """并行同步当前团队所有知识库的文档

        Args:
            db: 数据库会话
            team_id: 团队 ID

        Returns:
            {
                "message", "datasets_synced", "total_ragflow_docs",
                "new_docs", "updated_docs", "orphan_docs", "details"
            }
        """
        # 查询团队绑定的知识库
        result = await db.execute(
            select(TeamDataset).where(TeamDataset.team_id == team_id)
        )
        team_datasets = list(result.scalars().all())

        if not team_datasets:
            return {
                "message": "当前团队未绑定知识库",
                "datasets_synced": 0,
                "total_ragflow_docs": 0,
                "new_docs": 0,
                "updated_docs": 0,
                "orphan_docs": 0,
                "details": [],
            }

        # 顺序同步每个 dataset（共享 AsyncSession 不支持并发操作）
        results = []
        for ds in team_datasets:
            try:
                r = await self.sync_dataset(
                    db, team_id,
                    ds.ragflow_dataset_id,
                    ds.ragflow_dataset_name or ds.ragflow_dataset_id,
                    user_id=user_id,
                )
                results.append(r)
            except Exception as e:
                results.append(e)

        # 汇总结果
        details = []
        total_ragflow = 0
        total_new = 0
        total_updated = 0
        total_orphans = 0
        datasets_synced = 0

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error(f"同步 dataset 失败: {team_datasets[i].ragflow_dataset_id} - {r}")
                details.append({
                    "dataset_id": team_datasets[i].ragflow_dataset_id,
                    "dataset_name": team_datasets[i].ragflow_dataset_name or "",
                    "error": str(r),
                })
                continue

            details.append(r)
            total_ragflow += r["ragflow_count"]
            total_new += r["new"]
            total_updated += r["updated"]
            total_orphans += r["orphans"]
            datasets_synced += 1

        # 显式提交，确保同步结果在 response 返回前持久化
        await db.commit()

        return {
            "message": "同步完成",
            "datasets_synced": datasets_synced,
            "total_ragflow_docs": total_ragflow,
            "new_docs": total_new,
            "updated_docs": total_updated,
            "orphan_docs": total_orphans,
            "details": details,
        }
