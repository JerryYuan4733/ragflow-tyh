"""
RAGflow API 客户端
封装 RAGflow HTTP API，提供 Dataset/Document/Chunk/Session/Completion 操作
"""

import asyncio
import json
import logging
from typing import Optional, AsyncIterator

import httpx

from app.core.config import settings
from app.adapters.ragflow_types import (
    DatasetCreate, DatasetInfo,
    DocumentInfo,
    ChunkCreate, ChunkInfo,
    ChatAssistantInfo, SessionCreate, SessionInfo,
    CompletionChunk,
)

logger = logging.getLogger(__name__)

# 重试配置
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0


class RAGflowClient:
    """RAGflow HTTP API 客户端"""

    def __init__(self):
        self.base_url = settings.RAGFLOW_BASE_URL.rstrip("/")
        self.api_key = settings.RAGFLOW_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    def _create_client(self) -> httpx.AsyncClient:
        """创建新的 httpx 客户端实例"""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = self._create_client()
        return self._client

    def _reset_client(self):
        """连接失败时重置客户端，强制下次请求创建新实例"""
        if self._client and not self._client.is_closed:
            asyncio.get_event_loop().create_task(self._client.aclose())
        self._client = None

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        带重试的 HTTP 请求。
        连接失败时自动重建客户端并重试，解决瞬时连接故障问题。
        """
        last_exc = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await self.client.request(method.upper(), url, **kwargs)
                return resp
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_exc = e
                logger.warning(
                    f"[RAGFlow] 连接失败 (尝试 {attempt + 1}/{MAX_RETRIES + 1}): "
                    f"{type(e).__name__}: {e}"
                )
                # 重建客户端（连接池可能已损坏）
                self._reset_client()
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        raise last_exc  # type: ignore[misc]

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def update_connection(self, base_url: str, api_key: str):
        """动态更新 RAGFlow 连接配置（从系统设置页面调用）"""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # 关闭旧 client，下次请求自动用新配置创建
        if self._client and not self._client.is_closed:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._client.aclose())
                else:
                    loop.run_until_complete(self._client.aclose())
            except Exception:
                pass
        self._client = None

    def _check_response(self, resp: httpx.Response) -> dict:
        """统一响应检查"""
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") not in (0, 200, None):
            raise Exception(f"RAGflow API error: {data.get('message', 'Unknown error')}")
        return data

    # ==================== Dataset ====================

    async def create_dataset(self, params: DatasetCreate) -> DatasetInfo:
        """创建知识库"""
        resp = await self._request_with_retry("post", "/datasets", json=params.model_dump())
        data = self._check_response(resp)
        ds = data.get("data", {})
        return DatasetInfo(id=ds["id"], name=ds.get("name", ""), description=ds.get("description", ""))

    async def list_datasets(self, page: int = 1, size: int = 30) -> list[DatasetInfo]:
        """列出知识库"""
        resp = await self._request_with_retry("get", "/datasets", params={"page": page, "page_size": size})
        data = self._check_response(resp)
        return [DatasetInfo(**ds) for ds in data.get("data", [])]

    async def delete_dataset(self, dataset_id: str) -> bool:
        """删除知识库"""
        resp = await self._request_with_retry("delete", "/datasets", json={"ids": [dataset_id]})
        self._check_response(resp)
        return True

    # ==================== Document ====================

    async def upload_document(self, dataset_id: str, file_path: str, filename: str) -> DocumentInfo:
        """上传文档到知识库（基于文件路径）"""
        with open(file_path, "rb") as f:
            files = {"file": (filename, f)}
            resp = await self._request_with_retry(
                "post",
                f"/datasets/{dataset_id}/documents",
                files=files,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        data = self._check_response(resp)
        docs = data.get("data", [])
        if docs:
            doc = docs[0] if isinstance(docs, list) else docs
            return DocumentInfo(id=doc["id"], name=doc.get("name", filename))
        raise Exception("Upload returned no document info")

    async def upload_documents(
        self, dataset_id: str, files_data: list[tuple[str, bytes, str]]
    ) -> list[str]:
        """
        上传文档到知识库（基于内存字节）
        注意: 文件上传不能使用共享client，因为共享client的默认Content-Type: application/json
        会覆盖multipart/form-data导致上传失败
        """
        doc_ids = []
        for filename, content, content_type in files_data:
            files = {"file": (filename, content, content_type)}
            # 必须使用独立 client，避免共享client的 Content-Type: application/json 干扰
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=httpx.Timeout(300.0, connect=15.0),  # RAGFlow处理大文件上传需要较长时间
                proxy=None,
            ) as upload_client:
                resp = await upload_client.post(
                    f"/datasets/{dataset_id}/documents",
                    files=files,
                )
            data = self._check_response(resp)
            docs = data.get("data", [])
            if docs:
                doc = docs[0] if isinstance(docs, list) else docs
                doc_ids.append(doc["id"])
                logger.info(f"文档 {filename} 上传成功: doc_id={doc['id']}")
            else:
                logger.warning(f"文档 {filename} 上传返回空数据")
        return doc_ids

    async def update_document_parser(
        self, dataset_id: str, doc_id: str,
        chunk_method: str,
        parser_config: dict | None = None,
    ) -> bool:
        """
        更新文档的解析方式和参数配置
        chunk_method: naive/qa/manual/presentation/table/laws/paper/book/picture/one/tag
        parser_config: 解析参数配置（如 chunk_token_num, delimiter 等），为空时仅设置解析方式
        """
        body: dict = {"chunk_method": chunk_method}
        if parser_config:
            body["parser_config"] = parser_config
        try:
            resp = await self._request_with_retry(
                "put",
                f"/datasets/{dataset_id}/documents/{doc_id}",
                json=body,
            )
            self._check_response(resp)
            logger.info(
                f"文档 {doc_id} 解析方式已设为: {chunk_method}"
                f"{', parser_config已传递' if parser_config else ''}"
            )
            return True
        except Exception as e:
            logger.error(f"设置解析方式失败: {e}")
            return False

    async def start_parsing(self, dataset_id: str, document_ids: list[str]) -> bool:
        """
        触发文档解析（分块+向量化）
        POST /datasets/{dataset_id}/chunks  body: {"document_ids": [...]}
        """
        try:
            resp = await self._request_with_retry(
                "post",
                f"/datasets/{dataset_id}/chunks",
                json={"document_ids": document_ids},
            )
            self._check_response(resp)
            logger.info(f"已触发解析: dataset={dataset_id}, docs={document_ids}")
            return True
        except Exception as e:
            logger.error(f"触发解析失败: {e}")
            return False

    async def list_documents(self, dataset_id: str, page: int = 1, size: int = 30) -> list[DocumentInfo]:
        """列出知识库中的文档
        
        RAGFlow 返回格式: {"code": 0, "data": {"total": N, "docs": [...]}}
        """
        resp = await self._request_with_retry(
            "get",
            f"/datasets/{dataset_id}/documents",
            params={"page": page, "page_size": size},
        )
        data = self._check_response(resp)
        payload = data.get("data", {})
        # 兼容两种格式：{"docs": [...]} 或直接 [...]
        if isinstance(payload, dict):
            docs = payload.get("docs", [])
        elif isinstance(payload, list):
            docs = payload
        else:
            docs = []
        return [DocumentInfo(**doc) for doc in docs]

    async def delete_document(self, dataset_id: str, document_id: str) -> bool:
        """删除文档"""
        resp = await self._request_with_retry(
            "delete",
            f"/datasets/{dataset_id}/documents",
            json={"ids": [document_id]},
        )
        self._check_response(resp)
        return True

    async def parse_document(self, dataset_id: str, document_id: str) -> bool:
        """触发文档解析"""
        resp = await self._request_with_retry(
            "post",
            f"/datasets/{dataset_id}/chunks",
            json={"document_ids": [document_id]},
        )
        self._check_response(resp)
        return True

    async def get_document_status(self, dataset_id: str, document_id: str) -> DocumentInfo:
        """获取文档解析状态"""
        resp = await self._request_with_retry(
            "get",
            f"/datasets/{dataset_id}/documents",
            params={"id": document_id},
        )
        data = self._check_response(resp)
        docs = data.get("data", [])
        if docs:
            return DocumentInfo(**docs[0])
        raise Exception(f"Document {document_id} not found")

    # ==================== 文档筛选 ====================

    async def list_qa_documents(self, dataset_id: str) -> list[DocumentInfo]:
        """列出知识库中解析方式为 qa 的文档（兼容 chunk_method / parser_id）"""
        docs = await self.list_documents(dataset_id, page=1, size=100)
        return [d for d in docs if d.effective_parser == "qa"]

    async def get_document_chunk_count(self, dataset_id: str, document_id: str) -> int:
        """获取文档的 chunk 总数（仅请求 1 条以获取 total）"""
        resp = await self._request_with_retry(
            "get",
            f"/datasets/{dataset_id}/documents/{document_id}/chunks",
            params={"page": 1, "page_size": 1},
        )
        data = self._check_response(resp)
        chunk_data = data.get("data") or {}
        return chunk_data.get("total", 0)

    # ==================== Chunk ====================

    async def create_chunk(self, dataset_id: str, document_id: str, chunk: ChunkCreate) -> ChunkInfo:
        """创建手动Chunk (用于Q&A)"""
        resp = await self._request_with_retry(
            "post",
            f"/datasets/{dataset_id}/documents/{document_id}/chunks",
            json={"content": chunk.content, "important_keywords": chunk.important_keywords},
        )
        data = self._check_response(resp)
        c = data.get("data", {}).get("chunk", {})
        return ChunkInfo(id=c.get("id", ""), content=c.get("content", ""), document_id=document_id)

    async def list_chunks(self, dataset_id: str, document_id: str, page: int = 1) -> list[ChunkInfo]:
        """列出文档Chunks"""
        resp = await self._request_with_retry(
            "get",
            f"/datasets/{dataset_id}/documents/{document_id}/chunks",
            params={"page": page, "page_size": 30},
        )
        data = self._check_response(resp)
        return [ChunkInfo(**c) for c in data.get("data", {}).get("chunks", [])]

    async def list_all_chunks(self, dataset_id: str, document_id: str, max_pages: int = 200) -> list[dict]:
        """
        获取文档所有 chunks（自动分页），返回原始 dict 列表。
        默认 max_pages=200，page_size=100，最多支持 20000 个 chunks。
        注意: RAGFlow 对超范围页返回 {"data": null}，需要安全处理。
        """
        all_chunks: list[dict] = []
        page_size = 100
        consecutive_errors = 0
        for page in range(1, max_pages + 1):
            try:
                resp = await self._request_with_retry(
                    "get",
                    f"/datasets/{dataset_id}/documents/{document_id}/chunks",
                    params={"page": page, "page_size": page_size},
                )
                data = self._check_response(resp)
                # RAGFlow 超范围页返回 "data": null，需要用 or {} 兜底
                chunk_data = data.get("data") or {}
                chunks = chunk_data.get("chunks") or []
                if not chunks:
                    break
                all_chunks.extend(chunks)
                consecutive_errors = 0
                # 不足一页说明已取完
                if len(chunks) < page_size:
                    break
            except Exception as e:
                consecutive_errors += 1
                logger.warning(f"list_all_chunks: 第{page}页获取失败: {e}")
                if consecutive_errors >= 3:
                    logger.error(f"list_all_chunks: 连续3页失败，停止获取 document={document_id}")
                    break
        logger.info(f"list_all_chunks: document={document_id}, 共获取 {len(all_chunks)} chunks ({page} 页)")
        return all_chunks

    async def delete_chunk(self, dataset_id: str, document_id: str, chunk_id: str) -> bool:
        """删除Chunk"""
        resp = await self._request_with_retry(
            "delete",
            f"/datasets/{dataset_id}/documents/{document_id}/chunks",
            json={"chunk_ids": [chunk_id]},
        )
        self._check_response(resp)
        return True

    # ==================== Chat Assistant ====================

    async def list_chat_assistants(self) -> list[ChatAssistantInfo]:
        """列出对话助手"""
        resp = await self._request_with_retry("get", "/chats")
        data = self._check_response(resp)
        return [ChatAssistantInfo(**c) for c in data.get("data", [])]

    async def create_chat_assistant(self, name: str, dataset_ids: list[str]) -> ChatAssistantInfo:
        """创建对话助手"""
        resp = await self._request_with_retry("post", "/chats", json={
            "name": name,
            "dataset_ids": dataset_ids,
        })
        data = self._check_response(resp)
        return ChatAssistantInfo(**data.get("data", {}))

    async def get_chat_assistant(self, chat_id: str) -> Optional[dict]:
        """获取对话助手详情（含LLM配置）"""
        try:
            resp = await self._request_with_retry("get", "/chats", params={"id": chat_id})
            data = self._check_response(resp)
            items = data.get("data", [])
            return items[0] if items else None
        except Exception as e:
            logger.warning(f"Failed to get chat assistant info: {e}")
            return None

    # ==================== Session ====================

    async def create_session(self, chat_id: str, name: str = "新对话") -> SessionInfo:
        """创建对话Session"""
        resp = await self._request_with_retry(
            "post",
            f"/chats/{chat_id}/sessions",
            json={"name": name},
        )
        data = self._check_response(resp)
        return SessionInfo(**data.get("data", {}))

    async def list_sessions(self, chat_id: str) -> list[SessionInfo]:
        """列出Sessions"""
        resp = await self._request_with_retry("get", f"/chats/{chat_id}/sessions")
        data = self._check_response(resp)
        return [SessionInfo(**s) for s in data.get("data", [])]

    async def delete_session(self, chat_id: str, session_id: str) -> bool:
        """删除Session"""
        resp = await self._request_with_retry(
            "delete",
            f"/chats/{chat_id}/sessions",
            json={"ids": [session_id]},
        )
        self._check_response(resp)
        return True

    async def get_session_messages(self, chat_id: str, session_id: str) -> list[dict]:
        """获取 RAGFlow 会话的消息列表（含 reference），用于回填 SSE 流缺失的检索片段"""
        resp = await self._request_with_retry(
            "get",
            f"/chats/{chat_id}/sessions",
            params={"id": session_id},
        )
        data = self._check_response(resp)
        sessions = data.get("data", [])
        if not sessions:
            return []
        return sessions[0].get("messages", [])

    # ==================== Completion (SSE) ====================

    async def completion_stream(
        self, chat_id: str, session_id: str, question: str,
        thinking: bool = False,
    ) -> AsyncIterator[CompletionChunk]:
        """
        流式对话补全 (SSE)
        yield CompletionChunk 供调用方逐步返回给前端
        FR-39: 支持 thinking 参数，控制 LLM 深度推理模式
        """
        logger.info(f"[SSE] 开始流式请求: chat_id={chat_id}, session_id={session_id}, thinking={thinking}")
        request_body = {"question": question, "session_id": session_id, "stream": True}
        if thinking:
            request_body["enable_thinking"] = True
        async with self.client.stream(
            "POST",
            f"/chats/{chat_id}/completions",
            json=request_body,
            timeout=httpx.Timeout(120.0 if thinking else 60.0, connect=10.0),
        ) as response:
            response.raise_for_status()
            full_answer = ""
            last_reference = None
            line_count = 0
            buffer = ""  # 缓冲区处理跨行数据

            # 使用 aiter_raw 获取原始字节，然后用增量解码器处理
            import codecs
            decoder = codecs.getincrementaldecoder('utf-8')('replace')
            async for raw_chunk in response.aiter_raw():
                text_chunk = decoder.decode(raw_chunk, final=False)
                buffer += text_chunk
                
                # 按换行符分割，保留最后一个可能不完整的行
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    
                    line_count += 1
                    # 调试日志
                    logger.debug(f"[SSE] Line {line_count} (len={len(line)}): {line[:200]}")
                    
                    if not line.startswith("data:"):
                        continue

                    json_str = line[5:].strip()
                    
                    # 检查 [DONE] 标记（某些 API 使用）
                    if json_str == "[DONE]":
                        logger.info(f"[SSE] 流结束([DONE]), 总行数={line_count}, 完整答案长度={len(full_answer)}")
                        yield CompletionChunk(answer="", is_final=True, reference=last_reference)
                        return

                    try:
                        chunk_data = json.loads(json_str)
                        data = chunk_data.get("data")
                        
                        # RAGFlow 格式：
                        # - 内容: {"code": 0, "data": {"answer": "累积内容", "reference": {...}}}
                        # - 结束: {"code": 0, "data": True}  <-- 布尔值 True 表示流结束
                        
                        # 检查是否是流结束标记
                        if data is True:
                            logger.info(f"[SSE] 流结束(data=True), 总行数={line_count}, 完整答案长度={len(full_answer)}")
                            yield CompletionChunk(answer="", is_final=True, reference=last_reference)
                            return
                        
                        # 跳过非字典数据
                        if data is None or not isinstance(data, dict):
                            logger.debug(f"[SSE] 跳过非内容数据: data={data}")
                            continue
                        
                        # FR-39: 首个 data chunk 打印所有字段，用于诊断
                        if line_count <= 2 and isinstance(data, dict):
                            logger.info(f"[SSE] Chunk#{line_count} keys={list(data.keys())}, start_to_think={data.get('start_to_think')}, end_to_think={data.get('end_to_think')}")

                        answer = data.get("answer", "")
                        # FR-39: 检测 RAGFlow 深度思考标记
                        is_start_think = bool(data.get("start_to_think"))
                        is_end_think = bool(data.get("end_to_think"))

                        if is_start_think:
                            logger.info("[SSE] 深度思考开始 (start_to_think)")
                        if is_end_think:
                            logger.info("[SSE] 深度思考结束 (end_to_think)")

                        # RAGFlow SSE 返回的是增量内容（不是累积内容）
                        # 直接使用 answer 作为增量
                        if answer or is_start_think or is_end_think:
                            if answer:
                                full_answer += answer
                            yield CompletionChunk(
                                answer=answer,
                                reference=None,
                                start_to_think=is_start_think,
                                end_to_think=is_end_think,
                            )

                        if data.get("reference"):
                            last_reference = data["reference"]

                    except json.JSONDecodeError as e:
                        logger.warning(f"[SSE] JSON解析失败: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"[SSE] 处理异常: {e}")
                        continue
            
            # 处理缓冲区中剩余的数据
            if buffer.strip():
                logger.warning(f"[SSE] 缓冲区有剩余数据: {buffer[:100]}")
            
            # 如果没有收到 [DONE]，也要结束流
            logger.info(f"[SSE] 流结束(无DONE), 总行数={line_count}, 完整答案长度={len(full_answer)}")
            yield CompletionChunk(answer="", is_final=True, reference=last_reference)

    # ==================== Retrieval (QA 重复检测用) ====================

    async def retrieval(
        self, question: str, dataset_ids: list[str],
        similarity_threshold: float = 0.1, top_k: int = 1,
    ) -> list[dict]:
        """
        调用 RAGFlow 检索接口，返回相似度最高的 chunks。
        用于 QA 重复检测中的语义相似度匹配。
        """
        resp = await self._request_with_retry(
            "post",
            "/retrieval",
            json={
                "question": question,
                "dataset_ids": dataset_ids,
                "similarity_threshold": similarity_threshold,
                "top_k": top_k,
            },
            timeout=httpx.Timeout(15.0, connect=5.0),
        )
        data = self._check_response(resp)
        return data.get("data", {}).get("chunks", [])

    async def completion_sync(
        self, chat_id: str, session_id: str, question: str
    ) -> tuple[str, Optional[dict]]:
        """同步对话补全 (非流式，用于测试)"""
        resp = await self._request_with_retry(
            "post",
            f"/chats/{chat_id}/completions",
            json={"question": question, "session_id": session_id, "stream": False},
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        data = self._check_response(resp)
        result = data.get("data", {})
        return result.get("answer", ""), result.get("reference")


# 全局单例
ragflow_client = RAGflowClient()
