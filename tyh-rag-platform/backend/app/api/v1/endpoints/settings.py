"""
系统设置接口
chat-config get/put + knowledge-base get/put + audit-logs query
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.deps import require_kb_admin, require_it_admin
from app.db.session import get_db
from app.models import User, SystemConfig, OperationLog

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatConfigResponse(BaseModel):
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048
    similarity_threshold: float = 0.2
    top_n: int = 8


class ChatConfigUpdate(BaseModel):
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    similarity_threshold: Optional[float] = None
    top_n: Optional[int] = None


@router.get("/chat-config", response_model=ChatConfigResponse)
async def get_chat_config(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取对话配置"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "chat_config")
    )
    config = result.scalar_one_or_none()
    if config:
        import json
        return ChatConfigResponse(**json.loads(config.config_value))
    return ChatConfigResponse()


@router.put("/chat-config")
async def update_chat_config(
    request: ChatConfigUpdate,
    user: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新对话配置 (仅IT管理员)"""
    import json
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "chat_config")
    )
    config = result.scalar_one_or_none()

    values = {k: v for k, v in request.model_dump().items() if v is not None}
    if config:
        existing = json.loads(config.config_value)
        existing.update(values)
        config.config_value = json.dumps(existing)
        config.updated_by = user.id
    else:
        config = SystemConfig(
            id=str(uuid.uuid4()),
            config_key="chat_config",
            config_value=json.dumps(values),
            updated_by=user.id,
        )
        db.add(config)

    await db.flush()
    return {"message": "配置已更新"}


# ======================== 知识库管理 ========================

class KnowledgeBaseUpdate(BaseModel):
    assistant_id: str


@router.get("/knowledge-base")
async def get_knowledge_base_config(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取当前知识库配置 + RAGFlow 中可用的助手/知识库列表"""
    import json
    import logging
    from app.core.config import settings
    from app.adapters.ragflow_client import ragflow_client

    logger = logging.getLogger(__name__)

    # 1. 从数据库读取动态配置，回退到环境变量
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "knowledge_base")
    )
    config = result.scalar_one_or_none()

    if config:
        kb_config = json.loads(config.config_value)
        active_assistant_id = kb_config.get("assistant_id", "")
    else:
        active_assistant_id = ""

    # 2. 查询当前助手详情
    current_info = {}
    try:
        assistant = await ragflow_client.get_chat_assistant(active_assistant_id)
        if assistant:
            llm = assistant.get("llm", {}) or {}
            # RAGFlow 返回 datasets（对象列表），提取 ID
            raw_datasets = assistant.get("datasets", []) or []
            ds_ids = [d["id"] for d in raw_datasets if isinstance(d, dict) and "id" in d]
            current_info = {
                "assistant_id": active_assistant_id,
                "assistant_name": assistant.get("name", "未知"),
                "dataset_ids": ds_ids,
                "datasets": [{"id": d.get("id"), "name": d.get("name", "未知")} for d in raw_datasets if isinstance(d, dict)],
                "model_name": llm.get("model_name", "默认模型"),
                "temperature": llm.get("temperature"),
                "top_p": llm.get("top_p"),
            }
        else:
            current_info = {"assistant_id": active_assistant_id, "assistant_name": "（无法获取）"}
    except Exception as e:
        logger.warning(f"获取当前助手信息失败: {e}")
        current_info = {"assistant_id": active_assistant_id, "error": str(e)}

    # 3. 列出所有可用助手（含关联知识库）
    available_assistants = []
    try:
        assistants = await ragflow_client.list_chat_assistants()
        for a in assistants:
            # RAGFlow 的 datasets 字段在 list 接口可能不返回，需用 get 补全
            raw_ds = a.datasets or []
            if not raw_ds:
                try:
                    detail = await ragflow_client.get_chat_assistant(a.id)
                    raw_ds = (detail or {}).get("datasets", []) or []
                except Exception:
                    pass
            ds_ids = [d["id"] for d in raw_ds if isinstance(d, dict) and "id" in d]
            available_assistants.append({
                "id": a.id,
                "name": a.name,
                "dataset_ids": ds_ids,
                "datasets": [{"id": d.get("id"), "name": d.get("name")} for d in raw_ds if isinstance(d, dict)],
            })
    except Exception as e:
        logger.warning(f"列出助手失败: {e}")

    # 4. 列出所有知识库
    available_datasets = []
    try:
        datasets = await ragflow_client.list_datasets()
        for ds in datasets:
            available_datasets.append({
                "id": ds.id,
                "name": ds.name,
                "chunk_count": ds.chunk_count or ds.chunk_num,
                "document_count": ds.document_count or ds.doc_num,
            })
    except Exception as e:
        logger.error(f"列出知识库失败: {e}", exc_info=True)

    # 回退：如果 list_datasets 为空，从助手关联的知识库中提取
    if not available_datasets and available_assistants:
        seen = set()
        for asst in available_assistants:
            for ds in asst.get("datasets", []):
                if ds.get("id") and ds["id"] not in seen:
                    seen.add(ds["id"])
                    available_datasets.append({"id": ds["id"], "name": ds.get("name", "未知")})

    return {
        "current": current_info,
        "available_assistants": available_assistants,
        "available_datasets": available_datasets,
        "config_source": "database" if config else "environment",
    }


@router.put("/knowledge-base")
async def update_knowledge_base_config(
    request: KnowledgeBaseUpdate,
    user: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新知识库配置（切换助手）"""
    import json
    import logging
    from app.adapters.ragflow_client import ragflow_client

    logger = logging.getLogger(__name__)

    # 验证助手 ID 有效
    assistant = await ragflow_client.get_chat_assistant(request.assistant_id)
    if not assistant:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="无效的助手 ID，在 RAGFlow 中未找到")

    # 写入数据库
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "knowledge_base")
    )
    config = result.scalar_one_or_none()

    values = {"assistant_id": request.assistant_id}
    if config:
        config.config_value = json.dumps(values)
        config.updated_by = user.id
    else:
        config = SystemConfig(
            id=str(uuid.uuid4()),
            config_key="knowledge_base",
            config_value=json.dumps(values),
            updated_by=user.id,
        )
        db.add(config)

    await db.flush()

    logger.info(f"知识库配置已更新: assistant_id={request.assistant_id}, by={user.display_name}")
    return {
        "message": "知识库配置已更新",
        "assistant_id": request.assistant_id,
        "assistant_name": assistant.get("name", "未知"),
    }

@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """审计日志查询"""
    query = select(OperationLog)
    if action:
        query = query.where(OperationLog.action == action)
    if user_id:
        query = query.where(OperationLog.user_id == user_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(
        query.order_by(OperationLog.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "items": [
            {"id": l.id, "user_id": l.user_id, "action": l.action,
             "resource_type": l.resource_type, "resource_id": l.resource_id,
             "detail": l.detail, "ip_address": l.ip_address,
             "created_at": l.created_at.isoformat()}
            for l in logs
        ],
        "total": total,
    }


# ======================== RAGFlow 连接配置 ========================

class RAGFlowConnectionUpdate(BaseModel):
    ragflow_base_url: Optional[str] = None
    ragflow_api_key: Optional[str] = None


@router.get("/ragflow-connection")
async def get_ragflow_connection(
    _=Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取 RAGFlow 连接配置"""
    import json
    from app.core.config import settings as app_settings
    from app.adapters.ragflow_client import ragflow_client

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "ragflow_connection")
    )
    config = result.scalar_one_or_none()

    if config:
        values = json.loads(config.config_value)
        base_url = values.get("ragflow_base_url", app_settings.RAGFLOW_BASE_URL)
        api_key = values.get("ragflow_api_key", app_settings.RAGFLOW_API_KEY)
        source = "database"
    else:
        base_url = app_settings.RAGFLOW_BASE_URL
        api_key = app_settings.RAGFLOW_API_KEY
        source = "environment"

    # 掩码 API Key（只显示前8位和后4位）
    masked_key = api_key[:8] + "****" + api_key[-4:] if len(api_key) > 12 else "****"

    return {
        "ragflow_base_url": base_url,
        "ragflow_api_key_masked": masked_key,
        "ragflow_api_key_full": api_key,  # 前端需要回填input
        "config_source": source,
        "current_client_url": ragflow_client.base_url,
    }


@router.put("/ragflow-connection")
async def update_ragflow_connection(
    request: RAGFlowConnectionUpdate,
    user: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新 RAGFlow 连接配置"""
    import json
    import logging
    from app.adapters.ragflow_client import ragflow_client

    logger = logging.getLogger(__name__)

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "ragflow_connection")
    )
    config = result.scalar_one_or_none()

    values = {k: v for k, v in request.model_dump().items() if v is not None}
    if config:
        existing = json.loads(config.config_value)
        existing.update(values)
        config.config_value = json.dumps(existing)
        config.updated_by = user.id
    else:
        config = SystemConfig(
            id=str(uuid.uuid4()),
            config_key="ragflow_connection",
            config_value=json.dumps(values),
            updated_by=user.id,
        )
        db.add(config)

    await db.flush()

    # 热更新 ragflow_client
    new_url = values.get("ragflow_base_url", ragflow_client.base_url)
    new_key = values.get("ragflow_api_key", ragflow_client.api_key)
    ragflow_client.update_connection(new_url, new_key)
    logger.info(f"RAGFlow 连接配置已更新: url={new_url}, by={user.display_name}")

    return {"message": "RAGFlow 连接配置已更新"}


@router.post("/ragflow-connection/test")
async def test_ragflow_connection(
    request: RAGFlowConnectionUpdate,
    _=Depends(require_it_admin),
):
    """测试 RAGFlow 连接（不保存）"""
    import httpx

    base_url = (request.ragflow_base_url or "").rstrip("/")
    api_key = request.ragflow_api_key or ""

    if not base_url or not api_key:
        return {"success": False, "message": "API地址和KEY不能为空"}

    try:
        async with httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=httpx.Timeout(10.0, connect=5.0),
            proxy=None,
        ) as client:
            resp = await client.get("/chats", params={"page": 1, "page_size": 1})
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") not in (0, 200, None):
                return {"success": False, "message": f"API返回错误: {data.get('message', '未知错误')}"}
            assistant_count = len(data.get("data", []))
            return {"success": True, "message": f"连接成功！检测到 {assistant_count} 个对话助手"}
    except httpx.ConnectError:
        return {"success": False, "message": "连接失败: 无法连接到该地址，请检查URL是否正确"}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {"success": False, "message": "认证失败: API Key 无效"}
        return {"success": False, "message": f"HTTP错误: {e.response.status_code}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


async def load_ragflow_connection_from_db(db: AsyncSession):
    """应用启动时从数据库加载 RAGFlow 连接配置（如果有）"""
    import json
    import logging
    from app.adapters.ragflow_client import ragflow_client

    logger = logging.getLogger(__name__)
    try:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == "ragflow_connection")
        )
        config = result.scalar_one_or_none()
        if config:
            values = json.loads(config.config_value)
            url = values.get("ragflow_base_url")
            key = values.get("ragflow_api_key")
            if url and key:
                ragflow_client.update_connection(url, key)
                logger.info(f"从数据库加载 RAGFlow 连接配置: url={url}")
    except Exception as e:
        logger.warning(f"加载 RAGFlow 连接配置失败: {e}")


# ======================== 文档解析配置 ========================

import json as _json

# RAGFlow 解析方式说明（用户友好）
CHUNK_METHOD_OPTIONS = [
    {"value": "naive", "label": "通用模式", "desc": "适合大部分文档，自动拆分段落"},
    {"value": "qa", "label": "问答模式", "desc": "适合FAQ/问答表格，按行识别问题和答案"},
    {"value": "manual", "label": "手册模式", "desc": "适合有目录层级的PDF手册，按章节自动拆分"},
    {"value": "table", "label": "表格模式", "desc": "适合纯表格数据，保留表格结构"},
    {"value": "presentation", "label": "演示文稿模式", "desc": "适合PPT/幻灯片，按页面拆分"},
    {"value": "laws", "label": "法规模式", "desc": "适合法律法规/合同文书，按条款拆分"},
    {"value": "paper", "label": "论文模式", "desc": "适合学术论文，识别摘要/章节/参考文献"},
    {"value": "book", "label": "书籍模式", "desc": "适合长篇书籍，按章节拆分"},
    {"value": "one", "label": "整篇模式", "desc": "不拆分，将整个文档作为一个知识块"},
    {"value": "picture", "label": "图片/OCR模式", "desc": "适合扫描件或截图，先做文字识别再解析"},
    {"value": "tag", "label": "标签模式", "desc": "用于打标签的词库，不直接回答问题"},
]

# 文件类型友好名称
FILE_TYPE_LABELS = {
    ".xlsx": "Excel 表格 (.xlsx)",
    ".xls": "Excel 97 (.xls)",
    ".csv": "CSV 文件 (.csv)",
    ".docx": "Word 文档 (.docx)",
    ".doc": "Word 97 (.doc)",
    ".md": "Markdown (.md)",
    ".txt": "纯文本 (.txt)",
    ".pdf": "PDF 文档 (.pdf)",
    ".pptx": "PPT 演示文稿 (.pptx)",
    ".ppt": "PPT 97 (.ppt)",
    ".html": "HTML 网页 (.html)",
    ".json": "JSON 文件 (.json)",
    ".eml": "邮件 (.eml)",
}

# 默认映射
DEFAULT_PARSE_CONFIG = {
    ".xlsx": "qa", ".xls": "qa", ".csv": "qa",
    ".docx": "naive", ".doc": "naive", ".md": "naive", ".txt": "naive",
    ".pdf": "manual",
    ".pptx": "presentation", ".ppt": "presentation",
    ".html": "naive", ".json": "naive", ".eml": "naive",
}

# ============================================================
# PARSER_CONFIG_SCHEMA — 严格对齐 RAGFlow 源码
#   参考: web/src/pages/dataset/dataset-setting/configuration/
#   各模式参数范围来自 RAGFlow 前端组件定义
# ============================================================

# layout_recognize 下拉选项（仅非 naive 模式使用）
_LAYOUT_RECOGNIZE_OPTIONS = [
    {"value": "DeepDOC", "label": "DeepDOC（内置引擎）"},
    {"value": "Plain Text", "label": "纯文本提取"},
]

PARSER_CONFIG_SCHEMA = {
    # ---- naive 通用模式（严格对齐 RAGFlow General 模式） ----
    "naive": {
        "params": [
            # ─── 基础参数（对应 RAGFlow 上半区） ───
            {"key": "chunk_token_num", "label": "知识块大小", "desc": "每个分块的最大 token 数",
             "type": "number", "default": 512, "min": 0, "max": 2048, "step": 1, "level": "basic"},
            {"key": "delimiter", "label": "分段符号", "desc": "系统按这些符号拆分文档（如换行符等）",
             "type": "text", "default": "\n", "level": "basic"},
            {"key": "enable_children", "label": "启用子分块", "desc": "是否生成子分块用于检索（父子层级）",
             "type": "switch", "default": False, "level": "basic"},
            {"key": "children_delimiter", "label": "子分块分隔符", "desc": "子分块使用的分隔符",
             "type": "text", "default": "\n", "level": "basic"},
            # ─── 高级参数（对应 RAGFlow 下半区） ───
            {"key": "toc_extraction", "label": "PageIndex", "desc": "是否提取文档目录/页面索引结构",
             "type": "switch", "default": False, "level": "advanced"},
            {"key": "image_table_context_window", "label": "图表上下文窗口",
             "desc": "图片和表格的上下文窗口大小（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 256, "step": 1, "level": "advanced"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
            {"key": "html4excel", "label": "Excel转HTML", "desc": "将文档中的表格转为 HTML 格式保留结构",
             "type": "switch", "default": False, "level": "advanced"},
        ],
    },
    # ---- manual 手册模式（RAGFlow: layout_recognize + auto_keywords/questions） ----
    "manual": {
        "params": [
            {"key": "layout_recognize", "label": "版面识别引擎", "desc": "识别目录结构和层级标题",
             "type": "select", "default": "DeepDOC", "options": _LAYOUT_RECOGNIZE_OPTIONS, "level": "basic"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- presentation 演示文稿模式 ----
    "presentation": {
        "params": [
            {"key": "layout_recognize", "label": "版面识别引擎", "desc": "识别幻灯片中的文字排版和图片位置",
             "type": "select", "default": "DeepDOC", "options": _LAYOUT_RECOGNIZE_OPTIONS, "level": "basic"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- laws 法规模式 ----
    "laws": {
        "params": [
            {"key": "layout_recognize", "label": "版面识别引擎", "desc": "识别条款编号和层级结构",
             "type": "select", "default": "DeepDOC", "options": _LAYOUT_RECOGNIZE_OPTIONS, "level": "basic"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- paper 论文模式 ----
    "paper": {
        "params": [
            {"key": "layout_recognize", "label": "版面识别引擎", "desc": "识别双栏排版、摘要、参考文献等论文结构",
             "type": "select", "default": "DeepDOC", "options": _LAYOUT_RECOGNIZE_OPTIONS, "level": "basic"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- book 书籍模式 ----
    "book": {
        "params": [
            {"key": "layout_recognize", "label": "版面识别引擎", "desc": "识别书籍章节和层级结构",
             "type": "select", "default": "DeepDOC", "options": _LAYOUT_RECOGNIZE_OPTIONS, "level": "basic"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- one 整篇模式 ----
    "one": {
        "params": [
            {"key": "layout_recognize", "label": "版面识别引擎", "desc": "选择文档版面分析引擎",
             "type": "select", "default": "DeepDOC", "options": _LAYOUT_RECOGNIZE_OPTIONS, "level": "basic"},
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- picture 图片模式（RAGFlow: 仅 auto_keywords/questions） ----
    "picture": {
        "params": [
            {"key": "auto_keywords", "label": "自动关键词", "desc": "自动生成关键词数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 30, "step": 1, "level": "advanced"},
            {"key": "auto_questions", "label": "自动问题", "desc": "自动生成问题数量（0=关闭）",
             "type": "number", "default": 0, "min": 0, "max": 10, "step": 1, "level": "advanced"},
        ],
    },
    # ---- 无参数模式 ----
    "qa": {"params": []},
    "table": {"params": []},
    "tag": {"params": []},
    "resume": {"params": []},
}

# 有效的解析模式集合
VALID_CHUNK_METHODS = {
    "naive", "qa", "manual", "table", "presentation",
    "laws", "paper", "book", "one", "picture", "tag", "resume",
}


class ParseConfigUpdate(BaseModel):
    """PUT /settings/parse-config 请求体（FR-07: Pydantic 校验）"""
    method_map: dict[str, str] = {}
    parser_configs: dict[str, dict] = {}
    # 兼容前端旧字段名 config
    config: Optional[dict[str, str]] = None

    def get_method_map(self) -> dict[str, str]:
        """兼容前端发送 config 或 method_map 两种字段名"""
        return self.config or self.method_map

    @classmethod
    def validate_method_map_values(cls, method_map: dict[str, str]) -> None:
        """校验 method_map 中的值"""
        for ext, method in method_map.items():
            if not ext.startswith("."):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=422,
                    detail=f"扩展名必须以.开头: {ext}"
                )
            if method not in VALID_CHUNK_METHODS:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=422,
                    detail=f"无效的解析模式: {method}，允许值: {', '.join(sorted(VALID_CHUNK_METHODS))}"
                )


@router.get("/parse-config")
async def get_parse_config(
    _=Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取文档解析配置"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "parse_config")
    )
    config = result.scalar_one_or_none()

    current_map = dict(DEFAULT_PARSE_CONFIG)
    saved_parser_configs = {}
    if config:
        try:
            saved = _json.loads(config.config_value)
            if "method_map" in saved:
                current_map.update(saved["method_map"])
            elif isinstance(saved, dict) and not saved.get("parser_configs"):
                # 兼容旧格式（直接存 ext→method）
                current_map.update(saved)
            if "parser_configs" in saved:
                saved_parser_configs = saved["parser_configs"]
        except Exception:
            pass

    # 构建返回数据
    items = []
    for ext, method in current_map.items():
        items.append({
            "extension": ext,
            "file_type_label": FILE_TYPE_LABELS.get(ext, ext),
            "chunk_method": method,
        })

    # 构建每种解析方式的当前参数值（含旧数据兼容转换）
    method_configs = {}
    for method in PARSER_CONFIG_SCHEMA:
        defaults = _get_defaults_for_method(method)
        actual = dict(defaults)
        if method in saved_parser_configs:
            actual.update(saved_parser_configs[method])
        # NFR-01: 兼容转换（layout_recognize bool→string、过滤无效参数）
        method_configs[method] = _normalize_parser_config(method, actual)

    return {
        "items": sorted(items, key=lambda x: x["extension"]),
        "options": CHUNK_METHOD_OPTIONS,
        "config_source": "database" if config else "default",
        "parser_config_schema": PARSER_CONFIG_SCHEMA,
        "parser_configs": method_configs,
    }


@router.put("/parse-config")
async def update_parse_config(
    request: ParseConfigUpdate,
    user: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新文档解析配置（FR-07: Pydantic 校验）"""
    method_map = request.get_method_map()
    parser_configs = request.parser_configs

    # FR-07: 校验 method_map 中的值
    if method_map:
        ParseConfigUpdate.validate_method_map_values(method_map)

    save_data = {
        "method_map": method_map,
        "parser_configs": parser_configs,
    }

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "parse_config")
    )
    config = result.scalar_one_or_none()
    if config:
        config.config_value = _json.dumps(save_data, ensure_ascii=False)
        config.updated_by = user.id
    else:
        config = SystemConfig(
            id=str(uuid.uuid4()),
            config_key="parse_config",
            config_value=_json.dumps(save_data, ensure_ascii=False),
            updated_by=user.id,
        )
        db.add(config)
    await db.flush()

    # FR-02: 热更新 SandboxService 中的映射和参数缓存
    try:
        from app.services.sandbox_service import SandboxService
        if method_map:
            SandboxService.CHUNK_METHOD_MAP.update(method_map)
        if parser_configs:
            SandboxService.PARSER_CONFIGS.update(parser_configs)
        logger.info("解析配置已热更新（含 CHUNK_METHOD_MAP + PARSER_CONFIGS）")
    except Exception as e:
        logger.warning(f"热更新解析配置失败: {e}")

    return {"message": "解析配置已保存", "config": save_data}


# ======================== 默认解析模式 ========================

VALID_PARSE_MODES = {"auto", "manual"}


@router.get("/parse-mode")
async def get_parse_mode(
    _=Depends(require_kb_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取默认解析模式（auto=自动解析 / manual=仅上传）"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "default_parse_mode")
    )
    config = result.scalar_one_or_none()
    if config:
        try:
            value = _json.loads(config.config_value)
        except (_json.JSONDecodeError, TypeError):
            value = config.config_value
        return {"parse_mode": value}
    return {"parse_mode": "auto"}


@router.put("/parse-mode")
async def update_parse_mode(
    request: dict,
    user: User = Depends(require_it_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新默认解析模式（仅 IT 管理员）"""
    from fastapi import HTTPException

    parse_mode = request.get("parse_mode", "")
    if parse_mode not in VALID_PARSE_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的解析模式，允许值: {', '.join(VALID_PARSE_MODES)}"
        )

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.config_key == "default_parse_mode")
    )
    config = result.scalar_one_or_none()
    if config:
        config.config_value = _json.dumps(parse_mode)
        config.updated_by = user.id
    else:
        config = SystemConfig(
            id=str(uuid.uuid4()),
            config_key="default_parse_mode",
            config_value=_json.dumps(parse_mode),
            updated_by=user.id,
        )
        db.add(config)

    await db.flush()
    logger.info(f"默认解析模式已更新: {parse_mode}, by={user.display_name}")
    return {"message": "默认解析模式已更新", "parse_mode": parse_mode}


# ======================== 兼容工具函数 ========================

def _normalize_layout_recognize(value) -> str:
    """NFR-01: 将旧版布尔值转换为新版字符串枚举"""
    if isinstance(value, bool):
        return "DeepDOC" if value else "Plain Text"
    if isinstance(value, str) and value in ("DeepDOC", "Plain Text"):
        return value
    return "DeepDOC"  # 兜底默认值


def _normalize_parser_config(method: str, params: dict) -> dict:
    """NFR-01: 规范化单个模式的 parser_config，处理旧数据兼容"""
    normalized = dict(params)
    # layout_recognize: bool → string 转换
    if "layout_recognize" in normalized:
        normalized["layout_recognize"] = _normalize_layout_recognize(normalized["layout_recognize"])
    # 仅保留当前 schema 中定义的参数（忽略旧模式中的多余字段）
    schema = PARSER_CONFIG_SCHEMA.get(method)
    if schema is not None:
        valid_keys = {p["key"] for p in schema.get("params", [])}
        normalized = {k: v for k, v in normalized.items() if k in valid_keys}
    return normalized


def _get_defaults_for_method(method: str) -> dict:
    """从 PARSER_CONFIG_SCHEMA 提取指定模式的默认参数值"""
    schema = PARSER_CONFIG_SCHEMA.get(method, {})
    defaults = {}
    for param in schema.get("params", []):
        if param.get("type") == "group":
            # 嵌套 group：递归提取 children 默认值
            group_defaults = {}
            for child in param.get("children", []):
                if "default" in child:
                    group_defaults[child["key"]] = child["default"]
            defaults[param["key"]] = group_defaults
        elif "default" in param:
            defaults[param["key"]] = param["default"]
    return defaults


# ======================== 启动加载 ========================

async def load_parse_config_from_db(db):
    """应用启动时从数据库加载解析配置到 SandboxService 内存缓存"""
    from app.services.sandbox_service import SandboxService

    try:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == "parse_config")
        )
        config = result.scalar_one_or_none()
        if config:
            saved = _json.loads(config.config_value)
            if "method_map" in saved:
                SandboxService.CHUNK_METHOD_MAP.update(saved["method_map"])
            if "parser_configs" in saved:
                for method, params in saved["parser_configs"].items():
                    # 合并默认值 + 兼容转换
                    defaults = _get_defaults_for_method(method)
                    defaults.update(params)
                    normalized = _normalize_parser_config(method, defaults)
                    SandboxService.PARSER_CONFIGS[method] = normalized
            logger.info("从数据库加载解析配置完成")
        else:
            logger.info("数据库中无自定义解析配置，使用默认值")
    except Exception as e:
        logger.warning(f"加载解析配置失败: {e}")
