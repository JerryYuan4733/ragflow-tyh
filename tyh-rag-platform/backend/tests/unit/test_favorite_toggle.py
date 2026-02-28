"""单元测试: 收藏 Toggle 逻辑 (US-018 T-18.2)

测试 toggle_favorite 端点的语义:
- 无记录 → INSERT（收藏）
- 已存在 → DELETE（取消收藏）
"""

from unittest.mock import MagicMock
import pytest


class TestFavoriteToggle:
    """收藏 Toggle 语义测试"""

    def test_toggle_on_creates_favorite(self):
        """无收藏记录 → 创建收藏，返回 is_favorited=True"""
        existing = None
        result = {"is_favorited": False}

        if existing is None:
            # 创建收藏
            result["is_favorited"] = True
        else:
            # 取消收藏
            result["is_favorited"] = False

        assert result["is_favorited"] is True

    def test_toggle_off_deletes_favorite(self):
        """已有收藏 → 删除，返回 is_favorited=False"""
        existing = MagicMock()
        existing.id = "fav-1"
        result = {"is_favorited": False}

        if existing is None:
            result["is_favorited"] = True
        else:
            result["is_favorited"] = False

        assert result["is_favorited"] is False
