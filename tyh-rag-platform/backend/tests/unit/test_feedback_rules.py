"""单元测试: domain/rules/feedback_rules.py — 连续踩检测"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.domain.rules.feedback_rules import check_consecutive_dislikes


class TestCheckConsecutiveDislikes:
    """连续踩检测规则"""

    @pytest.mark.asyncio
    async def test_below_threshold_returns_false(self):
        """踩数 < 3 返回 False"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_db.execute.return_value = mock_result

        result = await check_consecutive_dislikes("sess-1", mock_db)
        assert result is False

    @pytest.mark.asyncio
    async def test_at_threshold_returns_true(self):
        """踩数 = 3 返回 True"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db.execute.return_value = mock_result

        result = await check_consecutive_dislikes("sess-1", mock_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_above_threshold_returns_true(self):
        """踩数 > 3 返回 True"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_db.execute.return_value = mock_result

        result = await check_consecutive_dislikes("sess-1", mock_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        """自定义阈值 = 5"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 4
        mock_db.execute.return_value = mock_result

        result = await check_consecutive_dislikes("sess-1", mock_db, threshold=5)
        assert result is False

        mock_result.scalar.return_value = 5
        result = await check_consecutive_dislikes("sess-1", mock_db, threshold=5)
        assert result is True

    @pytest.mark.asyncio
    async def test_zero_dislikes(self):
        """0踩返回 False"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await check_consecutive_dislikes("sess-1", mock_db)
        assert result is False

    @pytest.mark.asyncio
    async def test_null_count_returns_false(self):
        """数据库返回None时视为0"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await check_consecutive_dislikes("sess-1", mock_db)
        assert result is False
