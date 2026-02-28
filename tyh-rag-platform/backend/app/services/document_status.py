"""
文档状态常量与映射函数

将 RAGFlow 的 run 字段映射为管理系统的文档状态。
参考架构文档: docs/architecture/2026-02-25-1921-文档管理功能优化-架构设计-V1.md §3.3
"""

# ==================== RAGFlow run 字段常量 ====================

RAGFLOW_RUN_UNSTART = "0"
RAGFLOW_RUN_RUNNING = "1"
RAGFLOW_RUN_FAIL = "2"
RAGFLOW_RUN_DONE = "3"
RAGFLOW_RUN_CANCEL = "4"

# ==================== 管理系统文档状态常量 ====================

STATUS_PENDING = "pending"      # 待解析（已上传到 RAGFlow 但未触发解析）
STATUS_UPLOADING = "uploading"  # 上传中（前端瞬态，后端不持久化）
STATUS_PARSING = "parsing"      # 解析中（RAGFlow 正在解析）
STATUS_READY = "ready"          # 已完成（解析成功，可用于检索）
STATUS_ERROR = "error"          # 失败（解析失败/同步异常/上传失败）

# 允许触发解析的状态集合
PARSABLE_STATUSES = {STATUS_PENDING, STATUS_ERROR}

# 批量解析单次上限
BATCH_PARSE_LIMIT = 50

# ==================== 状态映射 ====================

# RAGFlow run 值 → 管理系统状态
_RAGFLOW_STATUS_MAPPING: dict[str, str] = {
    # 数字格式
    RAGFLOW_RUN_UNSTART: STATUS_PENDING,
    RAGFLOW_RUN_RUNNING: STATUS_PARSING,
    RAGFLOW_RUN_DONE: STATUS_READY,
    RAGFLOW_RUN_FAIL: STATUS_ERROR,
    RAGFLOW_RUN_CANCEL: STATUS_ERROR,
    # 小写文本格式
    "unstart": STATUS_PENDING,
    "running": STATUS_PARSING,
    "done": STATUS_READY,
    "fail": STATUS_ERROR,
    "cancel": STATUS_ERROR,
    # 大写文本格式（RAGFlow API 实际返回）
    "UNSTART": STATUS_PENDING,
    "RUNNING": STATUS_PARSING,
    "DONE": STATUS_READY,
    "FAIL": STATUS_ERROR,
    "CANCEL": STATUS_ERROR,
}


def map_ragflow_status(run: str) -> str:
    """将 RAGFlow run 字段映射为管理系统文档状态

    Args:
        run: RAGFlow 文档的 run 字段值（如 "0", "1", "done", "fail" 等）

    Returns:
        管理系统文档状态字符串: pending/parsing/ready/error
    """
    return _RAGFLOW_STATUS_MAPPING.get(str(run), STATUS_PENDING)
