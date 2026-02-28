"""
QA 重复检测服务
两级检测: 精确匹配 + 语义相似度 (阈值 >= 0.90)
"""

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QAMeta
from app.adapters.ragflow_client import ragflow_client
from app.services.team_service import TeamService

logger = logging.getLogger(__name__)

# QA 重复检测语义相似度阈值
SIMILARITY_THRESHOLD = 0.90


@dataclass
class DuplicateResult:
    """重复检测结果"""
    qa_id: str
    question: str
    match_type: str  # "exact" | "semantic"
    similarity: float


@dataclass
class SemanticResult:
    """语义匹配结果"""
    qa_id: str
    question: str
    similarity: float


async def _exact_match(
    db: AsyncSession,
    question: str,
    team_id: str,
    exclude_qa_id: Optional[str] = None,
) -> Optional[QAMeta]:
    """精确匹配：查询 qa_meta 表中是否存在完全相同的问题"""
    query = select(QAMeta).where(
        QAMeta.question == question,
        QAMeta.team_id == team_id,
    )
    if exclude_qa_id:
        query = query.where(QAMeta.id != exclude_qa_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()


async def _semantic_match(
    db: AsyncSession,
    question: str,
    team_id: str,
) -> Optional[SemanticResult]:
    """
    语义匹配：调用 RAGFlow 检索接口进行语义相似度检测。
    异常时降级返回 None（仅依赖精确匹配）。
    """
    try:
        # 获取团队绑定的知识库 ID 列表
        dataset_ids = await TeamService.get_team_dataset_ids(db, team_id)
        if not dataset_ids:
            logger.debug(f"团队 {team_id} 无绑定知识库，跳过语义检测")
            return None

        # 调用 RAGFlow retrieval API
        chunks = await ragflow_client.retrieval(
            question=question,
            dataset_ids=dataset_ids,
            similarity_threshold=SIMILARITY_THRESHOLD,
            top_k=1,
        )

        if chunks:
            chunk = chunks[0]
            similarity = chunk.get("similarity", 0)
            if similarity >= SIMILARITY_THRESHOLD:
                return SemanticResult(
                    qa_id=chunk.get("document_id", ""),
                    question=chunk.get("content", "")[:200],
                    similarity=similarity,
                )
    except Exception as e:
        logger.warning(f"语义检索失败，跳过语义重复检测: {e}")

    return None


class QADuplicateDetector:
    """
    QA 重复检测器（两级检测）

    Level 1: 精确匹配 — 查询数据库中是否有完全相同的 question
    Level 2: 语义相似度 — 调用 RAGFlow retrieval API，阈值 >= 0.90
    """

    @staticmethod
    async def check(
        db: AsyncSession,
        question: str,
        team_id: str,
        exclude_qa_id: Optional[str] = None,
    ) -> Optional[DuplicateResult]:
        """
        执行两级重复检测。
        返回 None 表示不重复，否则返回 DuplicateResult。
        """
        # Level 1: 精确匹配
        exact = await _exact_match(db, question, team_id, exclude_qa_id)
        if exact:
            return DuplicateResult(
                qa_id=exact.id,
                question=exact.question[:200],
                match_type="exact",
                similarity=1.0,
            )

        # Level 2: 语义相似度
        semantic = await _semantic_match(db, question, team_id)
        if semantic:
            return DuplicateResult(
                qa_id=semantic.qa_id,
                question=semantic.question,
                match_type="semantic",
                similarity=semantic.similarity,
            )

        return None
