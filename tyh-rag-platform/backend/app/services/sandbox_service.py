"""
RAGFlow 文档上传服务

核心逻辑:
- 文档上传 → 写入团队绑定的 dataset
- 上传后自动解析
- 对话时 → 从 team_configs 获取 assistant_id
"""

import os
import logging
from typing import Optional
from app.adapters.ragflow_client import ragflow_client

logger = logging.getLogger(__name__)


class SandboxService:
    """RAGFlow 文档上传与解析服务"""

    # 文件扩展名 → RAGFlow 解析方式映射（热更新）
    CHUNK_METHOD_MAP: dict[str, str] = {
        # Excel/CSV → Q&A问答模式
        ".xlsx": "qa", ".xls": "qa", ".csv": "qa",
        # Word/Markdown/Text → 通用模式
        ".docx": "naive", ".doc": "naive", ".md": "naive", ".txt": "naive",
        # PDF → 手册模式（适合有目录层级的文档）
        ".pdf": "manual",
        # PPT → 演示文稿模式
        ".pptx": "presentation", ".ppt": "presentation",
        # 其他
        ".html": "naive", ".json": "naive", ".eml": "naive",
    }

    # 解析模式 → parser_config 参数缓存（热更新）
    PARSER_CONFIGS: dict[str, dict] = {}

    @staticmethod
    def get_chunk_method(filename: str) -> str:
        """根据文件扩展名推断 RAGFlow 解析方式"""
        ext = os.path.splitext(filename)[1].lower()
        return SandboxService.CHUNK_METHOD_MAP.get(ext, "naive")

    @staticmethod
    def get_parser_config(chunk_method: str) -> dict:
        """获取指定解析模式的 parser_config（从热缓存读取）
        自动将 image_table_context_window 展开为 RAGFlow 需要的
        image_context_size + table_context_size
        """
        cfg = dict(SandboxService.PARSER_CONFIGS.get(chunk_method, {}))
        # 合并字段展开（对齐 RAGFlow saving-button.tsx 逻辑）
        if "image_table_context_window" in cfg:
            window = cfg.pop("image_table_context_window")
            cfg["image_context_size"] = window
            cfg["table_context_size"] = window
        return cfg

    @staticmethod
    async def upload_to_dataset(
        filename: str, content: bytes, content_type: str,
        dataset_id: str = "",
    ) -> Optional[str]:
        """
        上传文档到指定Dataset
        dataset_id 由团队级别配置传入
        Returns: ragflow_document_id or None
        """
        if not dataset_id:
            logger.warning("团队知识库未配置, 跳过RAGFlow上传")
            return None

        try:
            doc_ids = await ragflow_client.upload_documents(
                dataset_id, [(filename, content, content_type)]
            )
            if doc_ids:
                logger.info(f"文档 {filename} 上传到 dataset={dataset_id}, doc_id={doc_ids[0]}")
                return doc_ids[0]
        except Exception as e:
            logger.error(f"上传失败: {e}")
        return None

    @staticmethod
    async def auto_parse_document(
        filename: str, ragflow_doc_id: str,
        dataset_id: str = "",
    ) -> bool:
        """上传后自动设置解析方式并触发解析"""
        if not dataset_id or not ragflow_doc_id:
            return False

        chunk_method = SandboxService.get_chunk_method(filename)
        parser_config = SandboxService.get_parser_config(chunk_method)
        logger.info(f"自动解析: {filename} -> chunk_method={chunk_method}, parser_config keys={list(parser_config.keys())}")

        # 1. 设置解析方式 + parser_config
        updated = await ragflow_client.update_document_parser(
            dataset_id, ragflow_doc_id, chunk_method, parser_config or None
        )
        if not updated:
            logger.warning(f"设置解析方式失败，仍尝试触发解析: {filename}")

        # 2. 触发解析
        parsed = await ragflow_client.start_parsing(dataset_id, [ragflow_doc_id])
        if parsed:
            logger.info(f"文档 {filename} 已触发自动解析 (method={chunk_method})")
        else:
            logger.warning(f"触发解析失败: {filename}")
        return parsed

    @staticmethod
    async def delete_from_dataset(dataset_id: str, doc_id: str) -> bool:
        """从指定dataset删除文档"""
        if not dataset_id or not doc_id:
            return False
        try:
            await ragflow_client.delete_document(dataset_id, doc_id)
            logger.info(f"文档 {doc_id} 从 dataset={dataset_id} 删除成功")
            return True
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False


sandbox_service = SandboxService()
