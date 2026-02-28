"""敏感内容过滤器 (T-016)"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 竞品名称关键词
COMPETITOR_KEYWORDS = [
    "竞品A", "竞品B",  # 实际使用时替换为真实竞品名
]

# 虚假政策关键词
FAKE_POLICY_PATTERNS = [
    r"保证.*收益",
    r"承诺.*回报",
    r"零风险",
]

SAFE_REPLY = "⚠️ 该内容涉及敏感信息，无法显示。请联系管理员了解详情。"


def filter_content(text: str) -> tuple[str, bool]:
    """
    过滤敏感内容
    Returns: (过滤后文本, 是否被过滤)
    """
    if not text:
        return text, False

    # 检查竞品关键词
    for keyword in COMPETITOR_KEYWORDS:
        if keyword in text:
            logger.warning(f"Content filtered: competitor keyword '{keyword}'")
            return SAFE_REPLY, True

    # 检查虚假政策
    for pattern in FAKE_POLICY_PATTERNS:
        if re.search(pattern, text):
            logger.warning(f"Content filtered: fake policy pattern '{pattern}'")
            return SAFE_REPLY, True

    return text, False
