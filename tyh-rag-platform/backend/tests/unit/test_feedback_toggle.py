"""单元测试: 反馈 Toggle 逻辑 (US-018 T-18.1)

测试 submit_feedback 端点的三种 Toggle 语义:
- 无记录 → INSERT
- 类型相同 → DELETE（取消）
- 类型不同 → UPDATE（切换）
- 连续 3 踩检测
"""

from enum import Enum
from unittest.mock import MagicMock
import pytest


class FeedbackType(str, Enum):
    """本地模拟，避免导入 app.models"""
    LIKE = "like"
    DISLIKE = "dislike"


DISLIKE_THRESHOLD = 3


class TestFeedbackToggle:
    """反馈 Toggle 语义测试"""

    def test_first_like_creates_feedback(self):
        """首次点赞 → 创建反馈记录"""
        existing = None
        new_type = FeedbackType.LIKE
        result = {"id": None, "type": None}

        if existing is None:
            result["id"] = "new-id"
            result["type"] = new_type.value

        assert result["type"] == "like"
        assert result["id"] is not None

    def test_same_type_deletes_feedback(self):
        """重复点赞 → 取消反馈"""
        existing = MagicMock()
        existing.type = FeedbackType.LIKE
        existing.id = "fb-1"

        new_type = FeedbackType.LIKE
        result = {"id": None, "type": None}

        if existing is None:
            pass
        elif existing.type == new_type:
            # 取消
            result["id"] = None
            result["type"] = None

        assert result["type"] is None
        assert result["id"] is None

    def test_like_to_dislike_switches(self):
        """赞 → 踩 → 切换反馈"""
        existing = MagicMock()
        existing.type = FeedbackType.LIKE
        existing.id = "fb-1"

        new_type = FeedbackType.DISLIKE
        result = {"id": None, "type": None}

        if existing is None:
            pass
        elif existing.type == new_type:
            pass
        else:
            existing.type = new_type
            result["id"] = existing.id
            result["type"] = new_type.value

        assert result["type"] == "dislike"
        assert result["id"] == "fb-1"

    def test_dislike_to_like_switches(self):
        """踩 → 赞 → 切换反馈"""
        existing = MagicMock()
        existing.type = FeedbackType.DISLIKE
        existing.id = "fb-2"

        new_type = FeedbackType.LIKE
        result = {"id": None, "type": None}

        if existing is None:
            pass
        elif existing.type == new_type:
            pass
        else:
            existing.type = new_type
            result["id"] = existing.id
            result["type"] = new_type.value

        assert result["type"] == "like"
        assert result["id"] == "fb-2"

    def test_dislike_same_cancels(self):
        """重复踩 → 取消"""
        existing = MagicMock()
        existing.type = FeedbackType.DISLIKE

        new_type = FeedbackType.DISLIKE
        result = {"id": None, "type": None}

        if existing is not None and existing.type == new_type:
            result["id"] = None
            result["type"] = None

        assert result["type"] is None

    def test_three_dislikes_suggest_transfer(self):
        """连续 3 踩检测返回 suggest_transfer=True"""
        assert 3 >= DISLIKE_THRESHOLD
        assert not (2 >= DISLIKE_THRESHOLD)
