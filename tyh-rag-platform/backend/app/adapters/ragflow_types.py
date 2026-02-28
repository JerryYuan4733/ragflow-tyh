"""RAGflow API 类型定义"""

from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


# ========== Dataset ==========

class DatasetCreate(BaseModel):
    name: str
    description: str = ""
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    chunk_method: str = "naive"


class DatasetInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = ""
    chunk_count: int = 0
    chunk_num: int = 0
    document_count: int = 0
    doc_num: int = 0


# ========== Document ==========

class DocumentInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    size: int = 0
    type: str = ""
    status: str = ""
    chunk_count: int = 0
    chunk_num: int = 0
    progress: float = 0.0
    run: str = ""
    parser_id: str = ""             # 旧版字段（部分版本返回）
    chunk_method: str = ""          # RAGFlow 实际返回的解析方式字段 (naive/qa/...)

    @property
    def effective_parser(self) -> str:
        """统一获取解析方式：优先 chunk_method，兼容 parser_id"""
        return self.chunk_method or self.parser_id


# ========== Chunk ==========

class ChunkCreate(BaseModel):
    content: str
    important_keywords: list[str] = []


class ChunkInfo(BaseModel):
    id: str
    content: str
    document_id: str = ""
    important_keywords: list[str] = []


# ========== Chat/Session ==========

class ChatAssistantInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    dataset_ids: list[str] = []
    datasets: list[dict] = []  # RAGFlow 返回的完整知识库对象


class SessionCreate(BaseModel):
    name: str = "新对话"


class SessionInfo(BaseModel):
    id: str
    name: str
    chat_id: str = ""
    messages: list[dict] = []


# ========== Completion ==========

class CompletionChunk(BaseModel):
    """SSE流式回答片段"""
    answer: str = ""
    reference: Optional[dict[str, Any]] = None
    audio_binary: Optional[str] = None
    is_final: bool = False
    start_to_think: bool = False  # FR-39: RAGFlow 深度思考开始标记
    end_to_think: bool = False    # FR-39: RAGFlow 深度思考结束标记
